import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import serial.tools.list_ports

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
        self.track_assignments = {}  # Track assignment info
        self.available_ports = []  # List of available serial ports
        self.selected_port = None  # Current selected serial port

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
        tk.Button(root, text="退出", command=root.quit).grid(
            row=5, column=3, padx=10, pady=10, sticky="ew"
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
        try:
            # Get all available serial ports
            ports = serial.tools.list_ports.comports()
            self.available_ports = [port.device for port in ports]

            # Update combobox values
            port_descriptions = []
            for port in ports:
                # Display port name and description
                if port.description and port.description != "n/a":
                    port_descriptions.append(f"{port.device} - {port.description}")
                else:
                    port_descriptions.append(port.device)

            self.port_combo["values"] = port_descriptions

            # Try keeping previous selection if possible
            if self.selected_port and self.selected_port in self.available_ports:
                for i, desc in enumerate(port_descriptions):
                    if desc.startswith(self.selected_port):
                        self.port_combo.current(i)
                        break
            elif port_descriptions:
                # If no previous selection, select the first available port
                self.port_combo.current(0)
                self.selected_port = (
                    self.available_ports[0] if self.available_ports else None
                )
            else:
                # No available ports
                self.port_combo.set("无可用串口")
                self.selected_port = None

        except Exception as e:
            messagebox.showerror("错误", f"刷新串口失败: {e}")
            self.port_combo.set("刷新失败")
            logging.error(f"Error refreshing ports: {e}")
            self.selected_port = None

    def on_port_selected(self, event):
        """Handle serial port selection event"""
        selection = self.port_combo.current()
        if selection >= 0 and selection < len(self.available_ports):
            self.selected_port = self.available_ports[selection]
            logging.debug(f"Serial port selected: {self.selected_port}")

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
            default_node = track_num  # Default assignment is track number

            # Store default assignment
            self.track_assignments[i] = default_node

            # Insert row into treeview
            item_id = self.track_tree.insert(
                "", "end", values=(track_num, track_size, f"节点 {default_node}")
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

        def on_cancel():
            dialog.destroy()

        tk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
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
        if not self.selected_port:
            messagebox.showwarning("提示", "请先选择串口！")
            return

        # Send data in a new thread in case
        play_thread = threading.Thread(target=self._send_play_command, daemon=True)
        play_thread.start()

    def _send_play_command(self):
        """Worker thread to send play command"""
        hs.send_command(self.selected_port, bytes([0x30]))  # type: ignore

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

        # Transmit in a new thread to avoid blocking UI
        transmission_thread = threading.Thread(
            target=self._transmit_worker, daemon=True
        )
        transmission_thread.start()

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
        # Transmission start
        success_count = hs.send_music_data(self.selected_port, self.byte_list, self.track_assignments)  # type: ignore
        # Calculate expected transmissions
        expected_transmissions = len(self.byte_list) - self._count_unassigned_tracks()
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


if __name__ == "__main__":
    root = tk.Tk()
    app = MidiFilePlayer(root)
    root.mainloop()
