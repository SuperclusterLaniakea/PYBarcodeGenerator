"""
条形码生成器 - 功能完整的GUI应用（v2.4 最终修复版）

修复内容：
- 解决保存后找不到文件的问题（自动补全扩展名）
- 预览功能增强，具备容错能力
- 统一使用绝对路径，避免相对路径歧义
- 预览区固定大小，位于日志上方

依赖安装：
pip install python-barcode pillow
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageTk


class BarcodeGeneratorApp:
    BARCODE_TYPES = {
        "Code128": "code128",
        "Code39": "code39",
        "EAN-13": "ean13",
        "EAN-8": "ean8",
        "UPC-A": "upca",
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("条形码生成器")
        self.root.geometry("650x600")
        self.root.resizable(True, True)

        self.preview_image = None
        self.preview_label = None

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---------- 基本设置 ----------
        settings_frame = ttk.LabelFrame(main_frame, text="基本设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="条码类型：").grid(row=0, column=0, sticky=tk.W)
        self.barcode_type_var = tk.StringVar(value="Code128")
        type_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.barcode_type_var,
            values=list(self.BARCODE_TYPES.keys()),
            state="readonly",
            width=12
        )
        type_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 10))

        ttk.Label(settings_frame, text="输出目录：").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.output_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "barcodes"))
        dir_entry = ttk.Entry(settings_frame, textvariable=self.output_dir_var)
        dir_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(10, 0))
        browse_dir_btn = ttk.Button(settings_frame, text="浏览...", command=self.browse_output_dir)
        browse_dir_btn.grid(row=1, column=2, padx=(5, 0), pady=(10, 0))

        # ---------- 单个生成 ----------
        single_frame = ttk.LabelFrame(main_frame, text="单个生成", padding="10")
        single_frame.pack(fill=tk.X, pady=(0, 10))
        single_frame.columnconfigure(1, weight=1)

        ttk.Label(single_frame, text="输入内容：").grid(row=0, column=0, sticky=tk.W)
        self.single_entry = ttk.Entry(single_frame)
        self.single_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        self.single_entry.bind("<Return>", lambda e: self.generate_single())

        self.generate_btn = ttk.Button(single_frame, text="生成", command=self.generate_single)
        self.generate_btn.grid(row=0, column=2, padx=(5, 0))

        # ---------- 批量生成 ----------
        batch_frame = ttk.LabelFrame(main_frame, text="批量生成", padding="10")
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        batch_frame.columnconfigure(1, weight=1)

        ttk.Label(batch_frame, text="选择文件：").grid(row=0, column=0, sticky=tk.W)
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(batch_frame, textvariable=self.file_path_var, state="readonly")
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        self.browse_btn = ttk.Button(batch_frame, text="浏览...", command=self.browse_file)
        self.browse_btn.grid(row=0, column=2, padx=(5, 0))
        self.process_btn = ttk.Button(batch_frame, text="处理", command=self.process_batch)
        self.process_btn.grid(row=0, column=3, padx=(5, 0))

        self.progress = ttk.Progressbar(batch_frame, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        # ---------- 预览区（位于日志上方） ----------
        preview_frame = ttk.LabelFrame(main_frame, text="预览", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        preview_frame.config(width=400, height=150)
        preview_frame.pack_propagate(False)

        self.preview_label = ttk.Label(preview_frame, text="生成后预览", anchor=tk.CENTER)
        self.preview_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # ---------- 状态信息区 ----------
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)
        status_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)

        self.status_text = tk.Text(status_frame, height=6, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        clear_btn = ttk.Button(status_frame, text="清空状态", command=self.clear_status)
        clear_btn.grid(row=1, column=0, sticky=tk.E, pady=(5, 0))

        self.append_status("就绪。请设置参数并开始生成。")

    # ---------- 辅助方法 ----------
    def append_status(self, message: str):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()

    def clear_status(self):
        self.status_text.delete(1.0, tk.END)

    def sanitize_filename(self, name: str) -> str:
        """净化文件名，保留中文、字母、数字、下划线、连字符"""
        name = name.strip()
        name = re.sub(r'[^\w\s\-一-龥]', '_', name)
        name = name.strip()
        return name if name else "barcode"

    def ensure_output_dir(self):
        out_dir = os.path.abspath(self.output_dir_var.get())
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
            self.append_status(f"已创建输出目录：{out_dir}")

    def validate_input(self, content: str) -> str:
        btype = self.BARCODE_TYPES[self.barcode_type_var.get()]
        if btype in ("ean13", "ean8", "upca"):
            if not content.isdigit():
                return "EAN/UPC 条码只允许数字。"
            if btype == "ean13" and not (12 <= len(content) <= 13):
                return "EAN-13 需要12或13位数字。"
            if btype == "ean8" and not (7 <= len(content) <= 8):
                return "EAN-8 需要7或8位数字。"
            if btype == "upca" and not (11 <= len(content) <= 12):
                return "UPC-A 需要11或12位数字。"
        return ""

    def get_barcode_object(self, content: str):
        btype = self.BARCODE_TYPES[self.barcode_type_var.get()]
        code_class = barcode.get_barcode_class(btype)
        return code_class(content, writer=ImageWriter())

    # ---------- 浏览与预览 ----------
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(os.path.abspath(directory))
            self.append_status(f"输出目录已切换：{directory}")

    def preview_barcode(self, filepath: str):
        """
        在预览区显示条形码图片（增强容错版）
        - 自动补全缺失的 .png 后缀
        - 详细的错误提示
        """
        original_path = filepath
        # 1. 尝试原始路径
        if os.path.exists(filepath):
            pass
        else:
            # 2. 尝试追加 .png / .PNG 后缀
            for ext in ('.png', '.PNG'):
                candidate = filepath + ext
                if os.path.exists(candidate):
                    filepath = candidate
                    self.append_status(f"预览：自动补全后缀 → {filepath}")
                    break
            else:
                # 3. 都没找到，给出诊断信息
                self.preview_label.configure(image="", text="文件未找到")
                self.append_status(f"预览失败：文件不存在 → {original_path}")
                dir_part = os.path.dirname(original_path)
                if os.path.exists(dir_part):
                    try:
                        files = os.listdir(dir_part)
                        base = os.path.basename(original_path)
                        matching = [f for f in files if base in f]
                        if matching:
                            self.append_status(f"  目录中有相似文件：{matching}")
                    except Exception:
                        pass
                return

        # 尝试打开图片
        try:
            img = Image.open(filepath)
            img.thumbnail((380, 130), Image.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self.preview_image, text="")
        except Exception as e:
            self.preview_label.configure(image="", text="预览失败")
            self.append_status(f"预览图片时出错：{e}")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="选择文本文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.append_status(f"已选择文件：{file_path}")

    # ---------- 生成逻辑 ----------
    def generate_single(self):
        content = self.single_entry.get().strip()
        if not content:
            messagebox.showwarning("输入错误", "请输入要生成条形码的内容。")
            return
        error = self.validate_input(content)
        if error:
            messagebox.showerror("输入错误", error)
            return

        try:
            self.ensure_output_dir()
            barcode_obj = self.get_barcode_object(content)
            safe_name = self.sanitize_filename(content)
            filename = f"{safe_name}.png"
            full_path = os.path.abspath(os.path.join(self.output_dir_var.get(), filename))

            # 存在性检查
            if os.path.exists(full_path):
                result = messagebox.askyesno("文件已存在", f"文件 '{filename}' 已存在，是否覆盖？")
                if not result:
                    self.append_status(f"跳过生成：用户取消覆盖 '{filename}'")
                    return

            # 保存条形码
            barcode_obj.save(full_path, {
                'module_width': 0.2,
                'module_height': 15.0,
                'quiet_zone': 2,
                'font_size': 10,
                'text_distance': 5.0,
                'background': 'white',
                'foreground': 'black',
                'write_text': False
            })

            self.append_status(f"成功生成条形码：{filename}")
            # 预览（内部会尝试补全路径，无需再检查是否存在）
            self.preview_barcode(full_path)
            messagebox.showinfo("成功", f"条形码已保存为：\n{full_path}")

        except Exception as e:
            error_msg = f"生成失败：{str(e)}"
            self.append_status(error_msg)
            messagebox.showerror("生成错误", error_msg)

    def process_batch(self):
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("输入错误", "请先选择一个文本文件。")
            return
        if not os.path.exists(file_path):
            messagebox.showerror("文件错误", "指定的文件不存在。")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
        except PermissionError:
            messagebox.showerror("错误", "无法读取文件：权限不足。")
            return
        except UnicodeDecodeError:
            messagebox.showerror("错误", "文件编码错误：请确保文本文件为UTF-8编码。")
            return

        if not lines:
            messagebox.showinfo("提示", "文件中没有有效内容。")
            return

        self.ensure_output_dir()
        out_dir = os.path.abspath(self.output_dir_var.get())

        self.process_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)

        total = len(lines)
        self.progress["maximum"] = total
        self.progress["value"] = 0

        success_count = 0
        failed_count = 0

        self.append_status(f"开始批量处理 {total} 项...")

        try:
            for i, content in enumerate(lines, 1):
                error = self.validate_input(content)
                if error:
                    failed_count += 1
                    self.append_status(f"[{i}/{total}] 失败 '{content}': {error}")
                    self.progress["value"] = i
                    self.root.update_idletasks()
                    continue

                try:
                    barcode_obj = self.get_barcode_object(content)
                    safe_name = self.sanitize_filename(content)
                    filename = f"{safe_name}.png"
                    full_path = os.path.join(out_dir, filename)

                    barcode_obj.save(full_path, {
                        'module_width': 0.2,
                        'module_height': 15.0,
                        'quiet_zone': 2,
                        'font_size': 10,
                        'text_distance': 5.0,
                        'background': 'white',
                        'foreground': 'black',
                        'write_text': False
                    })
                    success_count += 1
                    self.append_status(f"[{i}/{total}] 成功: {filename}")
                except Exception as e:
                    failed_count += 1
                    self.append_status(f"[{i}/{total}] 失败 '{content}': {e}")

                self.progress["value"] = i
                self.root.update_idletasks()

            self.append_status(f"批量处理完成！总计: {total}, 成功: {success_count}, 失败: {failed_count}")
            messagebox.showinfo(
                "批量处理完成",
                f"总计处理: {total}\n成功: {success_count}\n失败: {failed_count}"
            )
        finally:
            self.process_btn.config(state=tk.NORMAL)
            self.browse_btn.config(state=tk.NORMAL)
            self.progress["value"] = 0

    # ---------- 菜单回调 ----------
    def show_help(self):
        help_text = (
            "条形码生成器 使用说明\n\n"
            "1. 选择条码类型（Code128 / Code39 / EAN 等）\n"
            "2. 设置输出目录（默认为程序目录下的 barcodes 文件夹）\n"
            "3. 单个生成：在输入框中填写内容，点击“生成”\n"
            "   - 对于 EAN/UPC 条码，请输入纯数字\n"
            "4. 批量生成：选择一个 UTF-8 编码的文本文件，每行一个内容\n"
            "5. 生成后可在预览区查看最后一张条形码\n\n"
            "预览失败时，程序会自动尝试补全 .png 扩展名，"
            "并列出目录中的相似文件。"
        )
        messagebox.showinfo("使用说明", help_text)

    def show_about(self):
        messagebox.showinfo(
            "关于",
            "条形码生成器 v2.4\n"
            "修复保存后预览路径问题，增强稳定性。"
        )


def main():
    try:
        root = tk.Tk()
        app = BarcodeGeneratorApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动失败", f"应用程序启动失败：\n{str(e)}")


if __name__ == "__main__":
    main()