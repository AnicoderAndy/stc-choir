import logging
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import serial

import host_serial as hs
import parse_midi as pm

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
)


class MidiFilePlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("STC-Choir 控制终端")

        # Configure grid column weights for even distribution
        for i in range(4):  # 4 columns (0, 1, 2, 3)
            self.root.grid_columnconfigure(i, weight=1)

        self.file_name = "未加载"
        self.is_playing = False
        self.byte_list = []
        self.unsynced_list = []  # List of unsynchronized tracks
        self.track_assignments = {}  # Track assignment info
        self.available_ports = []  # List of available serial ports
        self.selected_port: str = ""  # Current selected serial port
        self.opened_ser: serial.Serial | None = None  # Opened serial port object
        self.playback_thread: threading.Thread | None = None  # Playback thread
        self.enable_sync = True  # Sync flag
        self.baudrate = 115200  # Default baudrate
        self.sync_waiting_time: float = 0.1  # Default sync waiting time

        # Display filename
        tk.Label(root, text="文件:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.file_label = tk.Label(root, text=self.file_name, width=30, anchor="w")
        self.file_label.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="w")

        # Playback status
        tk.Label(root, text="状态:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.status_label = tk.Label(root, text="停止", width=10, anchor="w")
        self.status_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Serial port selection
        self.create_serial_port_selection()

        # Track table
        self.create_track_table()

        # Button
        tk.Button(root, text="加载文件", command=self.load_file).grid(
            row=5, column=0, padx=10, pady=10, sticky="ew"
        )
        tk.Button(root, text="传输音乐", command=self.transmit_music).grid(
            row=5, column=1, padx=10, pady=10, sticky="ew"
        )
        tk.Button(root, text="播放", command=self.play_music).grid(
            row=5, column=2, padx=10, pady=10, sticky="ew"
        )
        tk.Button(root, text="停止", command=self.stop_music).grid(
            row=5, column=3, padx=10, pady=10, sticky="ew"
        )
        tk.Button(root, text="选项设置", command=self.settings).grid(
            row=6, column=0, padx=10, pady=10, sticky="ew"
        )
        tk.Button(root, text="预置音乐", command=self.preset_music).grid(
            row=6, column=1, padx=10, pady=10, sticky="ew"
        )
        tk.Button(root, text="退出", command=self.root.quit).grid(
            row=6, column=2, padx=10, pady=10, sticky="ew", columnspan=2
        )

    def create_serial_port_selection(self):
        """Create interface for serial port selection"""
        # Serial port label
        tk.Label(self.root, text="串口:").grid(
            row=2, column=0, sticky="w", padx=10, pady=5
        )

        # Serial port combobox
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            self.root, textvariable=self.port_var, state="readonly", width=25
        )
        self.port_combo.grid(
            row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew"
        )
        self.port_combo.bind("<<ComboboxSelected>>", self.on_port_selected)

        # Refresh button
        tk.Button(self.root, text="刷新", command=self.refresh_ports).grid(
            row=2, column=3, padx=10, pady=5
        )

        # Initial port refresh
        self.refresh_ports()

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        if self.opened_ser:
            self.opened_ser.close()
        try:
            self.available_ports, port_descriptions = hs.get_serial_ports()
            self.port_combo["values"] = port_descriptions

            # Try keeping previous selection if possible
            if self.selected_port and self.selected_port in self.available_ports:
                for i, desc in enumerate(port_descriptions):
                    if desc.startswith(self.selected_port):
                        self.port_combo.current(i)
                        self.opened_ser = hs.open_serial_port(
                            self.selected_port, self.baudrate
                        )
                        break
            elif port_descriptions and self.available_ports:
                # If no previous selection, select the first available port
                self.port_combo.current(0)
                self.selected_port = self.available_ports[0]
                self.opened_ser = hs.open_serial_port(self.selected_port, self.baudrate)
            else:
                # No available ports
                self.port_combo.set("无可用串口")
                self.selected_port = ""

        except Exception as e:
            messagebox.showerror("错误", f"刷新串口失败: {e}")
            self.port_combo.set("刷新失败")
            logging.error(f"Error refreshing ports: {e}")
            self.selected_port = ""

    def on_port_selected(self, event):
        """Handle serial port selection event"""
        selection = self.port_combo.current()
        try:
            if self.opened_ser:
                self.opened_ser.close()
            if selection >= 0 and selection < len(self.available_ports):
                self.selected_port = self.available_ports[selection]
                logging.debug(f"Serial port selected: {self.selected_port}")
                self.opened_ser = hs.open_serial_port(self.selected_port, self.baudrate)
        except Exception as e:
            messagebox.showerror("错误", f"打开串口失败: {e}")
            logging.error(f"Error opening selected port: {e}")
            self.selected_port = ""
            self.opened_ser = None
            self.port_combo.set("打开失败")

    def create_track_table(self):
        # Track table label
        tk.Label(self.root, text="音轨分配:").grid(
            row=3, column=0, sticky="w", padx=10, pady=5
        )

        # Track table frame
        table_frame = tk.Frame(self.root)
        table_frame.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="ew")

        # Create Treeview for track table
        self.track_tree = ttk.Treeview(
            table_frame, columns=("编号", "大小", "分配节点"), show="headings", height=6
        )

        # Define column headings
        self.track_tree.heading("编号", text="编号")
        self.track_tree.heading("大小", text="大小")
        self.track_tree.heading("分配节点", text="分配至节点")

        # Configure column widths
        self.track_tree.column("编号", width=80, anchor="center")
        self.track_tree.column("大小", width=120, anchor="center")
        self.track_tree.column("分配节点", width=200, anchor="center")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.track_tree.yview
        )
        self.track_tree.configure(yscrollcommand=scrollbar.set)

        # Pack the treeview and scrollbar
        self.track_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click event to edit node assignment
        self.track_tree.bind("<Double-1>", self.on_track_double_click)

        # Store comboboxes for each track
        self.track_comboboxes = {}

    def update_track_table(self):
        """Update the track table with current byte_list data"""
        # Clear existing items
        for item in self.track_tree.get_children():
            self.track_tree.delete(item)

        # Clear comboboxes
        self.track_comboboxes.clear()

        if not self.byte_list:
            return

        # Add tracks to table
        for i, track_bytes in enumerate(self.byte_list):
            track_num = hex(i).upper()[2:]  # Convert to hex (0-F)
            track_size = len(track_bytes)

            # Check if track index exceeds available nodes (0-F, i.e., 0-15)
            if i > 15:
                default_node = "不分配"  # Assign to "unassigned" if track index > 15
            else:
                default_node = track_num  # Default assignment is track number

            # Store default assignment
            self.track_assignments[i] = default_node

            # Insert row into treeview
            display_assignment = (
                default_node if default_node == "不分配" else f"节点 {default_node}"
            )
            item_id = self.track_tree.insert(
                "", "end", values=(track_num, track_size, display_assignment)
            )

    def on_node_assignment_change(self, track_index, selected_value):
        """Process node assignment change"""
        self.track_assignments[track_index] = selected_value
        # Update the display in treeview
        items = self.track_tree.get_children()
        if track_index < len(items):
            item = items[track_index]
            values = list(self.track_tree.item(item, "values"))
            values[2] = f"节点 {selected_value}"
            self.track_tree.item(item, values=values)

    def on_track_double_click(self, event):
        """Process track double-click event to show node selection dialog"""
        selection = self.track_tree.selection()
        if not selection:
            return

        item = selection[0]
        item_index = self.track_tree.index(item)

        if item_index >= len(self.byte_list):
            return

        # Create and show node selection dialog
        self.show_node_selection_dialog(item_index)

    def show_node_selection_dialog(self, track_index):
        """Display node selection dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"选择音轨 {hex(track_index).upper()[2:]} 的分配节点")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry(
            "+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50)
        )

        tk.Label(dialog, text=f"音轨 {hex(track_index).upper()[2:]} 分配至:").pack(
            pady=10
        )

        # Create combobox (0-F + Skip) for node selection
        node_var = tk.StringVar()
        current_assignment = self.track_assignments.get(
            track_index, hex(track_index).upper()[2:]
        )
        node_var.set(current_assignment)

        node_options = ["不分配"] + [hex(i).upper()[2:] for i in range(16)]  # Skip, 0-F
        node_combo = ttk.Combobox(
            dialog, textvariable=node_var, values=node_options, state="readonly"
        )
        node_combo.pack(pady=10)

        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def on_ok():
            new_assignment = node_var.get()
            self.track_assignments[track_index] = new_assignment
            # update display in treeview
            items = self.track_tree.get_children()
            if track_index < len(items):
                item = items[track_index]
                values = list(self.track_tree.item(item, "values"))
                if new_assignment == "不分配":
                    values[2] = "不分配"
                else:
                    values[2] = f"节点 {new_assignment}"
                self.track_tree.item(item, values=values)
            dialog.destroy()

        def on_preview():
            selected_node = node_var.get()
            if (
                self.opened_ser
                and self.opened_ser.is_open
                and selected_node != "不分配"
            ):
                try:
                    hs.preview_track(
                        self.opened_ser,
                        int(selected_node, 16),
                        self.unsynced_list[track_index],
                    )
                except Exception as e:
                    messagebox.showerror("错误", f"预览失败: {e}")
                    logging.error(f"Error during preview: {e}")
            else:
                messagebox.showwarning("提示", "请先选择有效的串口和节点！")
            logging.info(
                f"Preview requested for track {track_index} on node {selected_node}"
            )

        def on_cancel():
            dialog.destroy()

        def on_stop():
            selected_node = node_var.get()
            logging.info(
                f"Stop requested for track {track_index} on node {selected_node}"
            )
            if (
                self.opened_ser
                and self.opened_ser.is_open
                and selected_node != "不分配"
            ):
                cmd = 0x60 | (int(selected_node, 16) & 0x0F)
                hs.send_command(self.opened_ser, bytes([cmd]))

        tk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="预览", command=on_preview).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(button_frame, text="停止", command=on_stop).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=on_cancel).pack(
            side=tk.LEFT, padx=5
        )

    def load_file(self):
        path = filedialog.askopenfilename(
            title="选择 MIDI 文件", filetypes=[("MIDI 文件", "*.mid")]
        )
        if path:
            self.file_name = path.split("/")[-1]
            self.file_label.config(text=self.file_name)
            self.is_playing = False
            self.status_label.config(text="停止")
            try:
                self.byte_list = pm.midi_to_binary_list(path, pm.MidiConfig())
                self.unsynced_list = pm.midi_to_binary_list(
                    path, pm.MidiConfig(enable_sync=False)
                )
                # Automatically update track table after file loaded
                self.update_track_table()
            except Exception as e:
                messagebox.showerror("错误", f"无法解析文件: {e}")
                self.file_name = "未加载"
                self.file_label.config(text=self.file_name + "（解析失败）")
                self.byte_list = []
                self.update_track_table()  # Clear the table
                return

    def play_music(self):
        """Send play command to firmware"""
        # Check if serial port is selected
        if not self.selected_port or not self.opened_ser:
            messagebox.showwarning("提示", "请先选择串口！")
            return

        # Send data in a new thread in case
        self.playback_thread = threading.Thread(
            target=self._playback_controller, daemon=True
        )
        self.playback_thread.start()

    def _playback_controller(self):
        """Worker thread to send play command"""
        if self.opened_ser and self.opened_ser.is_open:
            hs.send_command(self.opened_ser, bytes([0x30]))
        else:
            messagebox.showwarning("提示", "串口未打开！")
            logging.warning("Attempted to play music but serial port is not open.")
            return

        self.opened_ser.timeout = 0.1
        # Update UI status
        self.is_playing = True
        self.root.after(0, lambda: self.status_label.config(text="播放中"))

        while self.opened_ser:
            dt = self.opened_ser.read(1)
            if len(dt) == 1:
                if dt == b"\x70":
                    time.sleep(self.sync_waiting_time)
                    hs.send_command(self.opened_ser, bytes([0x80]))
                elif dt == b"\x20":
                    break
            if not self.is_playing:
                break

        self.opened_ser.timeout = 2.0
        self.root.after(0, lambda: self.status_label.config(text="停止"))
        logging.debug("Playback controller thread exiting")

    def stop_music(self):
        """Send stop command to firmware"""
        # Check if serial port is selected
        if not self.selected_port or not self.opened_ser:
            messagebox.showwarning("提示", "请先选择串口！")
            return
        self.opened_ser.timeout = 2.0
        # Send data in a new thread in case
        stop_thread = threading.Thread(target=self._send_stop_command, daemon=True)
        stop_thread.start()
        self.is_playing = False
        self.root.after(0, lambda: self.status_label.config(text="停止"))

    def _send_stop_command(self):
        """Worker thread to send stop command"""
        if self.opened_ser and self.opened_ser.is_open:
            hs.send_command(self.opened_ser, bytes([0x40]))
        else:
            messagebox.showwarning("提示", "串口未打开！")
            logging.warning("Attempted to stop music but serial port is not open.")

    def transmit_music(self):
        """Transmit music data to the firmware"""
        # Check if file is loaded
        if self.file_name == "未加载" or not self.byte_list:
            messagebox.showwarning("提示", "请先加载MIDI文件！")
            return

        # Check if serial port is selected
        if not self.selected_port:
            messagebox.showwarning("提示", "请先选择串口！")
            return

        # Check for node assignment conflicts
        conflict_info = self._check_node_assignment_conflicts()
        if conflict_info:
            conflict_message = "发现节点分配冲突：\n\n"
            for node, tracks in conflict_info.items():
                track_names = [f"音轨{hex(t).upper()[2:]}" for t in tracks]
                conflict_message += f"节点 {node}: {', '.join(track_names)}\n"
            conflict_message += "\n请重新分配音轨后再传输。"
            messagebox.showerror("节点分配冲突", conflict_message)
            return

        # Transmit in a new thread to avoid blocking UI
        transmission_thread = threading.Thread(
            target=self._transmit_worker, daemon=True
        )
        transmission_thread.start()

    def _check_node_assignment_conflicts(self):
        """Check for node assignment conflicts

        Returns:
            dict: Dictionary mapping conflicted node IDs to list of track indices,
                  empty dict if no conflicts
        """
        node_assignments = {}  # node_id -> list of track indices

        for track_index in range(len(self.byte_list)):
            node_id = self.track_assignments.get(
                track_index, hex(track_index).upper()[2:]
            )

            # Skip unassigned tracks
            if node_id == "不分配":
                continue

            # Skip tracks with invalid node assignments (should not happen with proper bounds checking)
            if node_id not in [hex(i).upper()[2:] for i in range(16)]:
                continue

            if node_id not in node_assignments:
                node_assignments[node_id] = []
            node_assignments[node_id].append(track_index)

        # Find conflicts (nodes with multiple tracks assigned)
        conflicts = {}
        for node_id, track_list in node_assignments.items():
            if len(track_list) > 1:
                conflicts[node_id] = track_list

        return conflicts

    def _count_unassigned_tracks(self):
        """Calculate number of unassigned tracks"""
        unassigned_count = 0
        for i in range(len(self.byte_list)):
            node_id = self.track_assignments.get(i, hex(i).upper()[2:])
            if node_id == "不分配":
                unassigned_count += 1
        return unassigned_count

    def _transmit_worker(self):
        """Worker thread to transmit music data"""
        if self.opened_ser and self.opened_ser.is_open:
            # Transmission start
            if not self.enable_sync:
                success_count = hs.send_music_data(
                    self.opened_ser, self.unsynced_list, self.track_assignments
                )
            else:
                success_count = hs.send_music_data(
                    self.opened_ser, self.byte_list, self.track_assignments
                )
            # Calculate expected transmissions
            expected_transmissions = (
                len(self.byte_list) - self._count_unassigned_tracks()
            )
            unassigned_count = self._count_unassigned_tracks()

            # Report results
            if success_count == expected_transmissions:
                if unassigned_count > 0:
                    message = f"成功传输 {success_count} 个轨道！（跳过 {unassigned_count} 个未分配轨道）"
                else:
                    message = f"所有 {success_count} 个轨道传输完成！"
                self.root.after(
                    0,
                    lambda: messagebox.showinfo("成功", message),
                )
            else:
                failed_count = expected_transmissions - success_count
                message = f"传输完成，但有 {failed_count} 个轨道失败"
                self.root.after(
                    0,
                    lambda: messagebox.showwarning("警告", message),
                )
        else:
            messagebox.showwarning("提示", "串口未打开！")
            logging.warning("Attempted to transmit music but serial port is not open.")

    def settings(self):
        """Open settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置")
        dialog.geometry("400x425")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center the dialog
        dialog.geometry(
            "+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100)
        )

        # Create main frame with padding
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Sync settings section
        sync_frame = tk.LabelFrame(main_frame, text="同步设置", padx=10, pady=10)
        sync_frame.pack(fill=tk.X, pady=(0, 15))

        self.sync_var = tk.BooleanVar()
        self.sync_var.set(self.enable_sync)

        sync_checkbox = tk.Checkbutton(
            sync_frame, text="启用音轨同步", variable=self.sync_var
        )
        sync_checkbox.pack(anchor="w")

        # Add description label
        sync_desc = tk.Label(
            sync_frame,
            text="若启用，此应用会读取 MIDI 文件中的同步标记，\n并在标记处尝试同步。",
            fg="gray",
            justify="left",
        )
        sync_desc.pack(anchor="w", pady=(5, 0))

        # Sync waiting time setting
        sync_time_frame = tk.Frame(sync_frame)
        sync_time_frame.pack(anchor="w", pady=(10, 0))

        tk.Label(sync_time_frame, text="同步等待时间 (秒):").pack(side=tk.LEFT)

        self.sync_waiting_var = tk.StringVar()
        self.sync_waiting_var.set(str(self.sync_waiting_time))

        sync_waiting_entry = tk.Entry(
            sync_time_frame,
            textvariable=self.sync_waiting_var,
            width=10,
            justify="center",
        )
        sync_waiting_entry.pack(side=tk.LEFT, padx=(10, 0))

        # Add description for sync waiting time
        sync_waiting_desc = tk.Label(
            sync_frame,
            text="设置每次同步等待的时间间隔，范围: 0.01-1.0 秒",
            fg="gray",
            justify="left",
        )
        sync_waiting_desc.pack(anchor="w", pady=(5, 0))

        # Baudrate settings section
        baudrate_frame = tk.LabelFrame(main_frame, text="串口设置", padx=10, pady=10)
        baudrate_frame.pack(fill=tk.X, pady=(0, 15))

        # Baudrate selection
        tk.Label(baudrate_frame, text="波特率:").pack(anchor="w")

        self.baudrate_var = tk.StringVar()
        self.baudrate_var.set(str(self.baudrate))

        baudrate_values = [
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
            "230400",
            "460800",
            "921600",
        ]
        baudrate_combo = ttk.Combobox(
            baudrate_frame,
            textvariable=self.baudrate_var,
            values=baudrate_values,
            state="readonly",
            width=15,
        )
        baudrate_combo.pack(anchor="w", pady=(5, 0))

        # Add description label
        baudrate_desc = tk.Label(
            baudrate_frame,
            text="除非你知道你在做什么，否则不要修改此设置。\n修改波特率后需要重新连接串口。",
            fg="gray",
            justify="left",
        )
        baudrate_desc.pack(anchor="w", pady=(5, 0))

        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        def on_ok():
            """Apply settings and close dialog"""
            old_baudrate = self.baudrate

            # Validate sync waiting time
            try:
                sync_waiting_time = float(self.sync_waiting_var.get())
                if not (0.01 <= sync_waiting_time <= 1.0):
                    messagebox.showerror(
                        "错误", "同步等待时间必须在 0.01 到 1.0 秒之间"
                    )
                    return
            except ValueError:
                messagebox.showerror("错误", "同步等待时间必须是有效的数字")
                return

            # Update settings
            self.enable_sync = self.sync_var.get()
            self.baudrate = int(self.baudrate_var.get())
            self.sync_waiting_time = sync_waiting_time

            # If baudrate changed and serial port is open, reconnect
            if (
                old_baudrate != self.baudrate
                and self.opened_ser
                and self.opened_ser.is_open
            ):
                try:
                    port = self.selected_port
                    self.opened_ser.close()
                    time.sleep(0.1)  # Brief delay for port to close
                    self.opened_ser = hs.open_serial_port(port, self.baudrate)
                    messagebox.showinfo(
                        "提示", f"串口已重新连接，波特率: {self.baudrate}"
                    )
                    logging.info(
                        f"Serial port reconnected with new baudrate: {self.baudrate}"
                    )
                except Exception as e:
                    messagebox.showerror("错误", f"重新连接串口失败: {e}")
                    logging.error(f"Failed to reconnect serial port: {e}")
                    self.opened_ser = None

            dialog.destroy()
            logging.info(
                f"Settings updated - Sync: {self.enable_sync}, Baudrate: {self.baudrate}, Sync waiting time: {self.sync_waiting_time}"
            )

        def on_cancel():
            """Cancel settings and close dialog"""
            dialog.destroy()

        def on_reset():
            """Reset to default values"""
            self.sync_var.set(True)
            self.baudrate_var.set("115200")
            self.sync_waiting_var.set("0.1")

        # Create buttons
        tk.Button(button_frame, text="确定", command=on_ok, width=8).pack(
            side=tk.LEFT, padx=(5, 0)
        )

        tk.Button(button_frame, text="取消", command=on_cancel, width=8).pack(
            side=tk.LEFT, padx=(5, 0)
        )

        tk.Button(button_frame, text="恢复默认", command=on_reset, width=8).pack(
            side=tk.RIGHT
        )

    def preset_music(self):
        """Open preset music selection dialog"""
        # Check if serial port is selected
        if not self.selected_port or not self.opened_ser:
            messagebox.showwarning("提示", "请先选择串口！")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("选择预置音乐")
        dialog.geometry("250x230")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center the dialog
        dialog.geometry(
            "+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100)
        )

        # Create main frame with padding
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title label
        tk.Label(main_frame, text="请选择预置音乐:").pack(pady=(0, 15))

        # Radio buttons for preset music selection
        self.preset_var = tk.IntVar()
        self.preset_var.set(0)  # Default to preset 0

        preset_options = [
            (0, "预置音乐 0"),
            (1, "预置音乐 1"),
            (2, "预置音乐 2"),
        ]

        for value, text in preset_options:
            radio = tk.Radiobutton(
                main_frame,
                text=text,
                variable=self.preset_var,
                value=value,
            )
            radio.pack(anchor="w", pady=2)

        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        def on_ok():
            """Send preset music command and close dialog"""
            selected_preset = self.preset_var.get()

            # Create command byte: 0x90, 0x91, or 0x92
            command_byte = 0x90 | (selected_preset & 0x0F)

            # Send command in a new thread
            preset_thread = threading.Thread(
                target=self._send_preset_command,
                args=(command_byte, selected_preset),
                daemon=True,
            )
            preset_thread.start()

            dialog.destroy()

        def on_cancel():
            """Cancel and close dialog"""
            dialog.destroy()

        # Create buttons
        tk.Button(button_frame, text="确定", command=on_ok, width=8).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        tk.Button(button_frame, text="取消", command=on_cancel, width=8).pack(
            side=tk.RIGHT
        )

    def _send_preset_command(self, command_byte, preset_number):
        """Worker thread to send preset music command"""
        if self.opened_ser and self.opened_ser.is_open:
            try:
                hs.send_command(self.opened_ser, bytes([command_byte]))
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "成功", f"已发送预置音乐 {preset_number} 指令"
                    ),
                )
                logging.info(
                    f"Preset music {preset_number} command sent: 0x{command_byte:02X}"
                )
            except Exception as e:
                self.root.after(
                    0, lambda: messagebox.showerror("错误", f"发送指令失败: {e}")
                )
                logging.error(f"Error sending preset command: {e}")
        else:
            self.root.after(0, lambda: messagebox.showwarning("提示", "串口未打开！"))
            logging.warning(
                "Attempted to send preset command but serial port is not open."
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = MidiFilePlayer(root)
    root.resizable(False, False)
    root.mainloop()
