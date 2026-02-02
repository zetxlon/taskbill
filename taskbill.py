import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None

APP_NAME = "TaskBill"
DB = "taskbill.db"


def money(x) -> str:
    # stable money formatting in rubles, 2 decimals
    d = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}"


def db():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    with db() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS client (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY,
            client_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(client_id, name),
            FOREIGN KEY(client_id) REFERENCES client(id) ON DELETE CASCADE
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS task (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            hours REAL NOT NULL CHECK(hours > 0),
            rate REAL NOT NULL CHECK(rate > 0),
            FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE
        )""")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — счета по задачам (без НДС)")
        self.geometry("980x560")
        self.minsize(900, 520)

        init_db()

        self._build_ui()
        self._binds()
        self.load_clients()

    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        tk.Button(top, text="➕ Клиент", command=self.add_client, width=14).pack(side="left", padx=4)
        tk.Button(top, text="➕ Проект", command=self.add_project, width=14).pack(side="left", padx=4)
        tk.Button(top, text="➕ Задача", command=self.add_task, width=14).pack(side="left", padx=4)
        tk.Button(top, text="✏️ Редакт.", command=self.edit_task, width=14).pack(side="left", padx=4)
        tk.Button(top, text="🗑 Удалить", command=self.delete_selected, width=14).pack(side="left", padx=4)

        tk.Button(top, text="📄 PDF-счёт", command=self.make_invoice, width=16).pack(side="right", padx=4)

        mid = tk.Frame(self)
        mid.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = tk.Frame(mid)
        left.pack(side="left", fill="y")

        self.clients = ttk.Treeview(left, columns=("name",), show="headings", height=18)
        self.clients.heading("name", text="Клиенты")
        self.clients.column("name", width=240, anchor="w")
        self.clients.pack(side="top", fill="y", expand=False)

        self.projects = ttk.Treeview(left, columns=("name",), show="headings", height=18)
        self.projects.heading("name", text="Проекты")
        self.projects.column("name", width=240, anchor="w")
        self.projects.pack(side="top", fill="y", expand=True, pady=(8, 0))

        right = tk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.tasks = ttk.Treeview(right, columns=("name", "hours", "rate", "sum"), show="headings")
        self.tasks.heading("name", text="Задача")
        self.tasks.heading("hours", text="Часы")
        self.tasks.heading("rate", text="₽/ч")
        self.tasks.heading("sum", text="Сумма ₽")

        self.tasks.column("name", width=420, anchor="w")
        self.tasks.column("hours", width=90, anchor="e")
        self.tasks.column("rate", width=110, anchor="e")
        self.tasks.column("sum", width=120, anchor="e")

        self.tasks.pack(fill="both", expand=True)

        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        self.total_var = tk.StringVar(value="Итого по проекту: 0.00 ₽")
        tk.Label(bottom, textvariable=self.total_var).pack(side="right")

    def _binds(self):
        self.clients.bind("<<TreeviewSelect>>", lambda e: self.load_projects())
        self.projects.bind("<<TreeviewSelect>>", lambda e: self.load_tasks())
        self.tasks.bind("<Double-1>", lambda e: self.edit_task())

    # -------- UTIL --------
    @staticmethod
    def _sel_iid(tree: ttk.Treeview):
        s = tree.selection()
        return int(s[0]) if s else None

    def _update_total(self):
        total = Decimal("0.00")
        for iid in self.tasks.get_children():
            vals = self.tasks.item(iid, "values")
            try:
                total += Decimal(str(vals[3]))
            except Exception:
                pass
        self.total_var.set(f"Итого по проекту: {total:.2f} ₽")

    # -------- LOAD --------
    def load_clients(self):
        self.clients.delete(*self.clients.get_children())
        self.projects.delete(*self.projects.get_children())
        self.tasks.delete(*self.tasks.get_children())
        self.total_var.set("Итого по проекту: 0.00 ₽")

        with db() as c:
            rows = c.execute("SELECT id, name FROM client ORDER BY name").fetchall()
        for rid, name in rows:
            self.clients.insert("", "end", iid=rid, values=(name,))

    def load_projects(self):
        self.projects.delete(*self.projects.get_children())
        self.tasks.delete(*self.tasks.get_children())
        self.total_var.set("Итого по проекту: 0.00 ₽")

        cid = self._sel_iid(self.clients)
        if not cid:
            return
        with db() as c:
            rows = c.execute("SELECT id, name FROM project WHERE client_id=? ORDER BY name", (cid,)).fetchall()
        for rid, name in rows:
            self.projects.insert("", "end", iid=rid, values=(name,))

    def load_tasks(self):
        self.tasks.delete(*self.tasks.get_children())
        self.total_var.set("Итого по проекту: 0.00 ₽")

        pid = self._sel_iid(self.projects)
        if not pid:
            return
        with db() as c:
            rows = c.execute("SELECT id, name, hours, rate FROM task WHERE project_id=? ORDER BY id", (pid,)).fetchall()

        for tid, name, hours, rate in rows:
            s = Decimal(str(hours)) * Decimal(str(rate))
            self.tasks.insert("", "end", iid=tid, values=(name, money(hours), money(rate), f"{s:.2f}"))

        self._update_total()

    # -------- ADD --------
    def add_client(self):
        name = simpledialog.askstring("Клиент", "Название клиента (например: ООО Ромашка)")
        if not name:
            return
        name = name.strip()
        if len(name) < 2:
            messagebox.showerror("Ошибка", "Название слишком короткое.")
            return

        with db() as c:
            try:
                c.execute("INSERT INTO client(name) VALUES(?)", (name,))
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Клиент уже существует.")
                return
        self.load_clients()

    def add_project(self):
        cid = self._sel_iid(self.clients)
        if not cid:
            messagebox.showerror("Ошибка", "Сначала выбери клиента.")
            return

        name = simpledialog.askstring("Проект", "Название проекта (например: Лендинг)")
        if not name:
            return
        name = name.strip()
        if len(name) < 2:
            messagebox.showerror("Ошибка", "Название слишком короткое.")
            return

        with db() as c:
            try:
                c.execute("INSERT INTO project(client_id, name) VALUES(?,?)", (cid, name))
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Такой проект у этого клиента уже есть.")
                return
        self.load_projects()

    def add_task(self):
        pid = self._sel_iid(self.projects)
        if not pid:
            messagebox.showerror("Ошибка", "Сначала выбери проект.")
            return

        name = simpledialog.askstring("Задача", "Название задачи (например: Верстка)")
        if not name:
            return
        name = name.strip()
        if len(name) < 2:
            messagebox.showerror("Ошибка", "Название слишком короткое.")
            return

        hours = simpledialog.askfloat("Часы", "Сколько часов?", minvalue=0.01)
        if hours is None:
            return
        rate = simpledialog.askfloat("Ставка", "Ставка ₽/час?", minvalue=0.01)
        if rate is None:
            return

        with db() as c:
            c.execute(
                "INSERT INTO task(project_id, name, hours, rate) VALUES(?,?,?,?)",
                (pid, name, float(hours), float(rate)),
            )
        self.load_tasks()

    # -------- EDIT/DELETE --------
    def edit_task(self):
        tid = self._sel_iid(self.tasks)
        if not tid:
            messagebox.showerror("Ошибка", "Выбери задачу (двойной клик тоже работает).")
            return

        with db() as c:
            row = c.execute("SELECT name, hours, rate FROM task WHERE id=?", (tid,)).fetchone()
        if not row:
            messagebox.showerror("Ошибка", "Задача не найдена.")
            return

        cur_name, cur_hours, cur_rate = row

        name = simpledialog.askstring("Редактировать задачу", "Название", initialvalue=str(cur_name))
        if not name:
            return
        name = name.strip()

        hours = simpledialog.askfloat("Редактировать задачу", "Часы", initialvalue=float(cur_hours), minvalue=0.01)
        if hours is None:
            return

        rate = simpledialog.askfloat("Редактировать задачу", "Ставка ₽/час", initialvalue=float(cur_rate), minvalue=0.01)
        if rate is None:
            return

        with db() as c:
            c.execute("UPDATE task SET name=?, hours=?, rate=? WHERE id=?", (name, float(hours), float(rate), tid))
        self.load_tasks()

    def delete_selected(self):
        tid = self._sel_iid(self.tasks)
        if tid:
            if not messagebox.askyesno("Удалить", "Удалить задачу?"):
                return
            with db() as c:
                c.execute("DELETE FROM task WHERE id=?", (tid,))
            self.load_tasks()
            return

        pid = self._sel_iid(self.projects)
        if pid:
            if not messagebox.askyesno("Удалить", "Удалить проект и все задачи в нём?"):
                return
            with db() as c:
                c.execute("DELETE FROM project WHERE id=?", (pid,))
            self.load_projects()
            return

        cid = self._sel_iid(self.clients)
        if cid:
            if not messagebox.askyesno("Удалить", "Удалить клиента и все его проекты/задачи?"):
                return
            with db() as c:
                c.execute("DELETE FROM client WHERE id=?", (cid,))
            self.load_clients()
            return

        messagebox.showerror("Ошибка", "Нечего удалять: ничего не выбрано.")

    # -------- PDF --------
    def make_invoice(self):
        if canvas is None:
            messagebox.showerror("Ошибка", "Не установлен reportlab. Установи: pip install reportlab")
            return

        pid = self._sel_iid(self.projects)
        if not pid:
            messagebox.showerror("Ошибка", "Сначала выбери проект.")
            return

        out = filedialog.asksaveasfilename(
            title="Сохранить PDF-счёт",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="schet.pdf",
        )
        if not out:
            return

        with db() as c:
            project = c.execute("SELECT name, client_id FROM project WHERE id=?", (pid,)).fetchone()
            if not project:
                messagebox.showerror("Ошибка", "Проект не найден.")
                return
            project_name, client_id = project
            client_name = c.execute("SELECT name FROM client WHERE id=?", (client_id,)).fetchone()[0]
            tasks = c.execute("SELECT name, hours, rate FROM task WHERE project_id=? ORDER BY id", (pid,)).fetchall()

        if not tasks:
            messagebox.showerror("Ошибка", "В проекте нет задач.")
            return

        total = Decimal("0.00")
        lines = []
        for name, hours, rate in tasks:
            s = Decimal(str(hours)) * Decimal(str(rate))
            total += s
            lines.append((str(name), Decimal(str(hours)), Decimal(str(rate)), s))

        pdf = canvas.Canvas(out, pagesize=A4)
        W, H = A4
        y = H - 60

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(50, y, "СЧЁТ"); y -= 30

        pdf.setFont("Helvetica", 11)
        pdf.drawString(50, y, f"Клиент: {client_name}"); y -= 18
        pdf.drawString(50, y, f"Проект: {project_name}"); y -= 18
        pdf.drawString(50, y, f"Дата: {date.today().isoformat()}"); y -= 28

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y, "Работы (без НДС):"); y -= 18
        pdf.setFont("Helvetica", 10)

        for (tname, thours, trate, tsum) in lines:
            if y < 80:
                pdf.showPage()
                y = H - 60
                pdf.setFont("Helvetica", 10)

            pdf.drawString(50, y, f"{tname}")
            pdf.drawRightString(W - 50, y, f"{thours:.2f} ч × {trate:.2f} ₽ = {tsum:.2f} ₽")
            y -= 16

        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "ИТОГО:")
        pdf.drawRightString(W - 50, y, f"{total:.2f} ₽ (без НДС)")
        y -= 30

        pdf.setFont("Helvetica", 9)
        pdf.drawString(50, y, "Оплата: переводом по реквизитам исполнителя (укажи в шаблоне при необходимости).")

        pdf.save()
        messagebox.showinfo("Готово", f"PDF-счёт создан:\n{out}")


if __name__ == "__main__":
    App().mainloop()
