import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime
import sys

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE DATABASE
# ─────────────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "aire_db",
}

# Limiti normativi UE/OMS utilizzati (tutti in µg/m³ salvo CO_8h in mg/m³)
# Fonte: Direttiva 2008/50/CE
LIMITI = {
    "NO2":   {"valore": 40,   "tipo": "media annuale",   "unita": "µg/m³"},
    "PM10":  {"valore": 50,   "tipo": "media 24h",       "unita": "µg/m³"},
    "PM25":  {"valore": 25,   "tipo": "media annuale",   "unita": "µg/m³"},
    "O3":    {"valore": 120,  "tipo": "media 8h",        "unita": "µg/m³"},
    "C6H6":  {"valore": 5,    "tipo": "media annuale",   "unita": "µg/m³"},
    "SO2":   {"valore": 125,  "tipo": "media 24h",       "unita": "µg/m³"},
    "CO_8h": {"valore": 10,   "tipo": "media 8h",        "unita": "mg/m³"},
}

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE
# ─────────────────────────────────────────────────────────────────────────────
BG          = "#F4F6F9"      
PANEL       = "#FFFFFF"      
TOPBAR_BG   = "#1C3557"      
TAB_ACTIVE  = "#FFFFFF"
TAB_IDLE    = "#263F61"
TAB_TEXT_A  = "#1C3557"
TAB_TEXT_I  = "#B0C4DE"
ACCENT      = "#2979FF"     
ACCENT2     = "#FF6D00"      
SUCCESS     = "#2E7D32"
DANGER      = "#C62828"
WARNING_COL = "#E65100"
TEXT        = "#1A1A2E"
TEXT_SUB    = "#5A6474"
BORDER      = "#DDE3EC"
ROW_ODD     = "#F9FAFB"
ROW_EVEN    = "#EEF2F7"

FONT        = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_TITLE  = ("Segoe UI", 14, "bold")
FONT_LARGE  = ("Segoe UI", 22, "bold")
FONT_KPI    = ("Segoe UI", 28, "bold")
FONT_SMALL  = ("Segoe UI", 8)

PLT_PALETTE = ["#2979FF","#FF6D00","#2E7D32","#C62828","#6A1B9A","#00838F","#AD1457"]


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
class DB:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
        except Error as e:
            messagebox.showerror("Errore connessione DB", str(e))
            sys.exit(1)

    def q(self, sql, params=None, write=False):
        try:
            cur = self.conn.cursor(dictionary=True)
            cur.execute(sql, params or ())
            if write:
                self.conn.commit()
                return cur.lastrowid
            return cur.fetchall()
        except Error as e:
            self.conn.rollback()
            raise e

    def close(self):
        if self.conn.is_connected():
            self.conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# WIDGET HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def panel(parent, **kw):
    return tk.Frame(parent, bg=PANEL, relief="flat", bd=0, **kw)

def label(parent, text, font=FONT, fg=TEXT, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg,
                    bg=parent.cget("bg"), **kw)

def entry(parent, width=18, **kw):
    f = tk.Frame(parent, bg=BORDER, bd=1)
    e = tk.Entry(f, width=width, relief="flat", font=FONT,
                 bg=PANEL, fg=TEXT, insertbackground=ACCENT, bd=4, **kw)
    e.pack()
    return f, e

def combo(parent, values, width=16, **kw):
    cb = ttk.Combobox(parent, values=values, width=width,
                      state="readonly", font=FONT, **kw)
    return cb

def btn(parent, text, cmd, bg=ACCENT, fg="white", pad=(14,6), **kw):
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg, font=FONT_BOLD,
                  relief="flat", bd=0, padx=pad[0], pady=pad[1],
                  activebackground=bg, activeforeground=fg,
                  cursor="hand2", **kw)
    return b

def separator(parent, orient="horizontal", color=BORDER):
    f = tk.Frame(parent,
                 height=1 if orient == "horizontal" else 0,
                 width=0 if orient == "horizontal" else 1,
                 bg=color)
    return f

def kpi_card(parent, title, var_val, color=ACCENT):
    f = tk.Frame(parent, bg=PANEL, padx=18, pady=14,
                 relief="solid", bd=1, highlightbackground=BORDER)
    accent_line = tk.Frame(f, bg=color, height=3)
    accent_line.pack(fill="x", pady=(0, 10))
    tk.Label(f, textvariable=var_val, font=FONT_KPI, fg=color, bg=PANEL).pack()
    tk.Label(f, text=title, font=FONT_BOLD, fg=TEXT_SUB, bg=PANEL).pack()
    return f

def matplotlib_fig(bg=PANEL):
    plt.rcParams.update({
        "figure.facecolor": bg,
        "axes.facecolor":   "#F8F9FC",
        "axes.edgecolor":   BORDER,
        "axes.labelcolor":  TEXT_SUB,
        "xtick.color":      TEXT_SUB,
        "ytick.color":      TEXT_SUB,
        "text.color":       TEXT,
        "grid.color":       BORDER,
        "grid.linestyle":   "--",
        "grid.alpha":       0.6,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TAB BAR + CONTENT SWITCHER
# ─────────────────────────────────────────────────────────────────────────────
class TabBar(tk.Frame):
    def __init__(self, parent, tabs, on_change, **kw):
        super().__init__(parent, bg=TOPBAR_BG, pady=0, **kw)
        self._btns = {}
        self._on_change = on_change
        for key, label_text, icon in tabs:
            b = tk.Button(self, text=f"  {icon}  {label_text}  ",
                          font=("Segoe UI", 10),
                          bg=TAB_IDLE, fg=TAB_TEXT_I,
                          relief="flat", bd=0,
                          padx=6, pady=14,
                          activebackground=PANEL,
                          activeforeground=TAB_TEXT_A,
                          cursor="hand2",
                          command=lambda k=key: self._select(k))
            b.pack(side="left")
            self._btns[key] = b

    def _select(self, key):
        for k, b in self._btns.items():
            if k == key:
                b.config(bg=TAB_ACTIVE, fg=TAB_TEXT_A)
            else:
                b.config(bg=TAB_IDLE, fg=TAB_TEXT_I)
        self._on_change(key)

    def set_active(self, key):
        self._select(key)


# ─────────────────────────────────────────────────────────────────────────────
# SCHERMATA 1 — DASHBOARD HOME
# ─────────────────────────────────────────────────────────────────────────────
class HomeView(tk.Frame):
    def __init__(self, parent, db: DB):
        super().__init__(parent, bg=BG)
        self.db = db
        self._build()

    def _build(self):

        hdr = tk.Frame(self, bg=BG, pady=20, padx=28)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Dashboard", font=FONT_LARGE, fg=TEXT, bg=BG).pack(side="left")
        tk.Label(hdr, text="  Qualità dell'aria nel Comune di Milano — 2025",
                 font=FONT, fg=TEXT_SUB, bg=BG).pack(side="left", anchor="s", pady=4)

        kpi_row = tk.Frame(self, bg=BG, padx=20, pady=0)
        kpi_row.pack(fill="x")

        kpis = self._get_kpis()
        colors = [ACCENT, ACCENT2, SUCCESS, DANGER]
        for (title, val), color in zip(kpis, colors):
            var = tk.StringVar(value=val)
            card = kpi_card(kpi_row, title, var, color)
            card.pack(side="left", expand=True, fill="both", padx=8, pady=4)

        separator(self).pack(fill="x", padx=28, pady=12)

        charts_row = tk.Frame(self, bg=BG)
        charts_row.pack(fill="both", expand=True, padx=20, pady=0)
        charts_row.columnconfigure(0, weight=3)
        charts_row.columnconfigure(1, weight=2)
        charts_row.rowconfigure(0, weight=1)

        left = panel(charts_row, padx=14, pady=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(8,4), pady=8)
        tk.Label(left, text="Media giornaliera PM10 e PM2.5 — anno 2025",
                 font=FONT_BOLD, fg=TEXT, bg=PANEL).pack(anchor="w", pady=(0,8))
        self._chart_serie(left)

        right = panel(charts_row, padx=14, pady=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(4,8), pady=8)
        tk.Label(right, text="Media per inquinante",
                 font=FONT_BOLD, fg=TEXT, bg=PANEL).pack(anchor="w", pady=(0,8))
        self._chart_bar(right)

    def _get_kpis(self):
        try:
            n_mis = self.db.q("SELECT COUNT(*) n FROM misurazioni")[0]["n"]
            n_sta = self.db.q("SELECT COUNT(*) n FROM stazioni")[0]["n"]
            n_inq = self.db.q("SELECT COUNT(*) n FROM inquinanti")[0]["n"]
            sup = sum(
                self.db.q("SELECT COUNT(*) n FROM misurazioni WHERE inquinante=%s AND valore>%s",
                          (k, v["valore"]))[0]["n"]
                for k, v in LIMITI.items()
            )
            return [
                ("Misurazioni totali", f"{n_mis:,}"),
                ("Stazioni attive",    str(n_sta)),
                ("Inquinanti",         str(n_inq)),
                ("Superamenti limite", str(sup)),
            ]
        except:
            return [("—","—")] * 4

    def _chart_serie(self, parent):
        matplotlib_fig()
        try:
            rows = self.db.q(
                "SELECT data_rilevazione d, inquinante i, AVG(valore) v "
                "FROM misurazioni WHERE inquinante IN ('PM10','PM25') "
                "GROUP BY data_rilevazione, inquinante ORDER BY data_rilevazione")
        except:
            rows = []

        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        if rows:
            from collections import defaultdict
            series = defaultdict(lambda: ([], []))
            for r in rows:
                d = r["d"] if not isinstance(r["d"], str) else datetime.strptime(r["d"], "%Y-%m-%d").date()
                series[r["i"]][0].append(d)
                series[r["i"]][1].append(r["v"])
            for i, (inq, (dates, vals)) in enumerate(series.items()):
                ax.plot(dates, vals, linewidth=1.2, label=inq,
                        color=PLT_PALETTE[i], alpha=0.75)
                import numpy as np
                if len(vals) >= 7:
                    mm = np.convolve(vals, np.ones(7)/7, mode='valid')
                    ax.plot(dates[3:-3], mm, linewidth=2,
                            color=PLT_PALETTE[i], label=f"{inq} (7gg)")
            lim_pm10 = LIMITI["PM10"]["valore"]
            lim_pm25 = LIMITI["PM25"]["valore"]
            ax.axhline(lim_pm10, color=PLT_PALETTE[0], linestyle=":", linewidth=1,
                       alpha=0.6, label=f"Limite PM10 ({lim_pm10})")
            ax.axhline(lim_pm25, color=PLT_PALETTE[1], linestyle=":", linewidth=1,
                       alpha=0.6, label=f"Limite PM25 ({lim_pm25})")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("µg/m³", fontsize=8)
        ax.legend(fontsize=7, ncol=2, loc="upper right")
        ax.grid(True, alpha=0.4)
        fig.tight_layout(pad=1.2)
        c = FigureCanvasTkAgg(fig, parent)
        c.get_tk_widget().pack(fill="both", expand=True)
        c.draw()

    def _chart_bar(self, parent):
        matplotlib_fig()
        try:
            rows = self.db.q(
                "SELECT inquinante, AVG(valore) media FROM misurazioni "
                "GROUP BY inquinante ORDER BY media DESC")
        except:
            rows = []
        fig, ax = plt.subplots(figsize=(4.2, 3.2))
        if rows:
            labels = [r["inquinante"] for r in rows]
            values = [r["media"] for r in rows]
            colors = [PLT_PALETTE[i % len(PLT_PALETTE)] for i in range(len(labels))]
            bars = ax.barh(labels, values, color=colors, alpha=0.85, height=0.55)
            for bar, v in zip(bars, values):
                ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                        f"{v:.1f}", va="center", fontsize=8, color=TEXT_SUB)
        ax.set_xlabel("Media µg/m³ (o mg/m³ per CO)", fontsize=7)
        ax.grid(True, axis="x", alpha=0.4)
        fig.tight_layout(pad=1.2)
        c = FigureCanvasTkAgg(fig, parent)
        c.get_tk_widget().pack(fill="both", expand=True)
        c.draw()


# ─────────────────────────────────────────────────────────────────────────────
# SCHERMATA 2 — MISURAZIONI (CRUD)
# ─────────────────────────────────────────────────────────────────────────────
class MisurazioniView(tk.Frame):
    def __init__(self, parent, db: DB):
        super().__init__(parent, bg=BG)
        self.db = db
        self._sel_id = None
        self._build()
        self._load_opts()
        self._refresh()

    def _build(self):
        
        left = panel(self, width=280)
        left.pack(side="left", fill="y", padx=(16,0), pady=16)
        left.pack_propagate(False)

       
        tk.Label(left, text="Filtri ricerca", font=FONT_BOLD, fg=TEXT, bg=PANEL).pack(anchor="w", padx=14, pady=(14,4))
        separator(left, color=BORDER).pack(fill="x", padx=14, pady=4)

        flt = tk.Frame(left, bg=PANEL, padx=14)
        flt.pack(fill="x")

        def frow(parent, text):
            tk.Label(parent, text=text, font=FONT_SMALL, fg=TEXT_SUB, bg=PANEL).pack(anchor="w", pady=(6,1))

        frow(flt, "Stazione")
        self.cb_flt_staz = combo(flt, [], width=22)
        self.cb_flt_staz.pack(fill="x")

        frow(flt, "Inquinante")
        self.cb_flt_inq = combo(flt, [], width=22)
        self.cb_flt_inq.pack(fill="x")

        frow(flt, "Data da (AAAA-MM-GG)")
        _, self.e_da = entry(flt, width=22)
        flt.winfo_children()[-1].pack(fill="x")

        frow(flt, "Data a (AAAA-MM-GG)")
        _, self.e_a = entry(flt, width=22)
        flt.winfo_children()[-1].pack(fill="x")

        btn_flt = tk.Frame(flt, bg=PANEL)
        btn_flt.pack(fill="x", pady=10)
        btn(btn_flt, "Cerca", self._refresh, bg=ACCENT).pack(side="left", padx=(0,6))
        btn(btn_flt, "Reset", self._reset, bg=TEXT_SUB).pack(side="left")

        separator(left, color=BORDER).pack(fill="x", padx=14, pady=10)

       
        tk.Label(left, text="Inserisci / Modifica", font=FONT_BOLD, fg=TEXT, bg=PANEL).pack(anchor="w", padx=14, pady=(0,4))

        frm = tk.Frame(left, bg=PANEL, padx=14)
        frm.pack(fill="x")

        frow(frm, "Stazione")
        self.cb_frm_staz = combo(frm, [], width=22)
        self.cb_frm_staz.pack(fill="x")

        frow(frm, "Inquinante")
        self.cb_frm_inq = combo(frm, [], width=22)
        self.cb_frm_inq.pack(fill="x")

        frow(frm, "Data (AAAA-MM-GG)")
        _, self.e_data = entry(frm, width=22)
        frm.winfo_children()[-1].pack(fill="x")

        frow(frm, "Valore")
        _, self.e_val = entry(frm, width=22)
        frm.winfo_children()[-1].pack(fill="x")

        crud_row = tk.Frame(frm, bg=PANEL)
        crud_row.pack(fill="x", pady=10)
        btn(crud_row, "+ Inserisci",  self._insert, bg=SUCCESS,      fg="white").pack(fill="x", pady=2)
        btn(crud_row, "↻ Aggiorna",   self._update, bg=ACCENT,       fg="white").pack(fill="x", pady=2)
        btn(crud_row, "✕ Elimina",    self._delete, bg=DANGER,        fg="white").pack(fill="x", pady=2)
        btn(crud_row, "Deseleziona",  self._desel,  bg=TEXT_SUB,     fg="white").pack(fill="x", pady=2)

        
        right = tk.Frame(self, bg=BG)
        right.pack(side="right", fill="both", expand=True, padx=16, pady=16)

        
        top_r = tk.Frame(right, bg=BG)
        top_r.pack(fill="x", pady=(0,8))
        tk.Label(top_r, text="Misurazioni", font=FONT_TITLE, fg=TEXT, bg=BG).pack(side="left")
        self.lbl_count = tk.Label(top_r, text="", font=FONT_SMALL, fg=TEXT_SUB, bg=BG)
        self.lbl_count.pack(side="left", padx=10, anchor="s", pady=4)

        
        style = ttk.Style()
        style.configure("Light.Treeview",
                        background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, rowheight=26, font=FONT)
        style.configure("Light.Treeview.Heading",
                        background=BG, foreground=TEXT_SUB, font=FONT_BOLD)
        style.map("Light.Treeview",
                  background=[("selected", "#DDEEFF")],
                  foreground=[("selected", TEXT)])

        tree_frame = panel(right)
        tree_frame.pack(fill="both", expand=True)

        cols = ("ID","Data","Stazione","Inquinante","Valore")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Light.Treeview", height=20)
        widths = [50,100,200,100,80]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col, command=lambda c=col: self._sort(c))
            self.tree.column(col, width=w, anchor="center")

        self.tree.tag_configure("odd",  background=ROW_ODD)
        self.tree.tag_configure("even", background=ROW_EVEN)

        sb_v = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        sb_h = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side="right",  fill="y")
        sb_h.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)

    def _load_opts(self):
        staz = self.db.q("SELECT id_stazione, area_interessata FROM stazioni ORDER BY id_stazione")
        s_vals = ["Tutte"] + [f"{r['id_stazione']} – {r['area_interessata']}" for r in staz]
        self.cb_flt_staz["values"] = s_vals; self.cb_flt_staz.set("Tutte")
        frm_s = s_vals[1:]
        self.cb_frm_staz["values"] = frm_s

        inq = self.db.q("SELECT inquinante FROM inquinanti ORDER BY inquinante")
        i_vals = [r["inquinante"] for r in inq]
        self.cb_flt_inq["values"] = ["Tutti"] + i_vals; self.cb_flt_inq.set("Tutti")
        self.cb_frm_inq["values"] = i_vals

    def _refresh(self):
        q = ("SELECT m.id_misurazione, m.data_rilevazione, s.area_interessata, "
             "m.inquinante, m.valore "
             "FROM misurazioni m JOIN stazioni s ON m.id_stazione=s.id_stazione "
             "WHERE 1=1")
        p = []
        staz = self.cb_flt_staz.get()
        if staz not in ("Tutte",""):
            p.append(int(staz.split("–")[0].strip()))
            q += " AND m.id_stazione=%s"
        inq = self.cb_flt_inq.get()
        if inq not in ("Tutti",""):
            q += " AND m.inquinante=%s"; p.append(inq)
        da = self.e_da.get().strip()
        a  = self.e_a.get().strip()
        if da: q += " AND m.data_rilevazione>=%s"; p.append(da)
        if a:  q += " AND m.data_rilevazione<=%s"; p.append(a)
        q += " ORDER BY m.data_rilevazione DESC LIMIT 500"
        try:
            rows = self.db.q(q, p)
        except Error as e:
            messagebox.showerror("Errore", str(e)); return

        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            d = r["data_rilevazione"]
            d_str = d.strftime("%Y-%m-%d") if hasattr(d,"strftime") else str(d)
            tag = "odd" if i % 2 else "even"
            self.tree.insert("","end", iid=r["id_misurazione"],
                             values=(r["id_misurazione"], d_str,
                                     r["area_interessata"], r["inquinante"],
                                     f"{r['valore']:.2f}"),
                             tags=(tag,))
        self.lbl_count.config(text=f"{len(rows)} record")

    def _reset(self):
        self.cb_flt_staz.set("Tutte"); self.cb_flt_inq.set("Tutti")
        self.e_da.delete(0,"end"); self.e_a.delete(0,"end")
        self._refresh()

    def _sort(self, col):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:    data.sort(key=lambda x: float(x[0]))
        except: data.sort()
        for i, (_, k) in enumerate(data):
            self.tree.move(k, "", i)

    def _on_sel(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        self._sel_id = int(sel[0])
        vals = self.tree.item(sel[0])["values"]
        
        for v in self.cb_frm_staz["values"]:
            if vals[2] in v:
                self.cb_frm_staz.set(v); break
        self.cb_frm_inq.set(vals[3])
        self.e_data.delete(0,"end"); self.e_data.insert(0, vals[1])
        self.e_val.delete(0,"end");  self.e_val.insert(0, vals[4])

    def _desel(self):
        self._sel_id = None
        self.tree.selection_remove(*self.tree.selection())
        self.cb_frm_staz.set(""); self.cb_frm_inq.set("")
        self.e_data.delete(0,"end"); self.e_val.delete(0,"end")

    def _form_vals(self):
        staz = self.cb_frm_staz.get()
        if not staz: raise ValueError("Seleziona una stazione.")
        sid = int(staz.split("–")[0].strip())
        inq = self.cb_frm_inq.get()
        if not inq: raise ValueError("Seleziona un inquinante.")
        data = self.e_data.get().strip()
        datetime.strptime(data, "%Y-%m-%d")
        valore = float(self.e_val.get().strip())
        return sid, inq, data, valore

    def _insert(self):
        try:
            sid, inq, d, v = self._form_vals()
            self.db.q("INSERT INTO misurazioni (id_stazione,inquinante,data_rilevazione,valore) "
                      "VALUES (%s,%s,%s,%s)", (sid,inq,d,v), write=True)
            messagebox.showinfo("Inserito","Misurazione inserita con successo.")
            self._refresh()
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _update(self):
        if not self._sel_id:
            messagebox.showwarning("Attenzione","Seleziona prima una riga."); return
        try:
            sid, inq, d, v = self._form_vals()
            self.db.q("UPDATE misurazioni SET id_stazione=%s,inquinante=%s,"
                      "data_rilevazione=%s,valore=%s WHERE id_misurazione=%s",
                      (sid,inq,d,v,self._sel_id), write=True)
            messagebox.showinfo("Aggiornato","Misurazione aggiornata.")
            self._refresh()
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _delete(self):
        if not self._sel_id:
            messagebox.showwarning("Attenzione","Seleziona prima una riga."); return
        if not messagebox.askyesno("Conferma",f"Eliminare la misurazione {self._sel_id}?"): return
        try:
            self.db.q("DELETE FROM misurazioni WHERE id_misurazione=%s",
                      (self._sel_id,), write=True)
            messagebox.showinfo("Eliminato","Misurazione eliminata.")
            self._sel_id = None; self._refresh()
        except Error as e:
            messagebox.showerror("Errore", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# SCHERMATA 3 — GRAFICI
# ─────────────────────────────────────────────────────────────────────────────
class GraficiView(tk.Frame):
    def __init__(self, parent, db: DB):
        super().__init__(parent, bg=BG)
        self.db = db
        self._canvas = None
        self._build()

    def _build(self):
        
        toolbar = panel(self, padx=16, pady=10)
        toolbar.pack(fill="x", padx=16, pady=(16,0))

        tk.Label(toolbar, text="Inquinante:", font=FONT, fg=TEXT_SUB, bg=PANEL).pack(side="left")
        inq_vals = [r["inquinante"] for r in self.db.q(
            "SELECT inquinante FROM inquinanti ORDER BY inquinante")]
        staz_rows = self.db.q("SELECT id_stazione, area_interessata FROM stazioni ORDER BY id_stazione")

        self.cb_inq = combo(toolbar, inq_vals, width=10)
        self.cb_inq.set(inq_vals[0] if inq_vals else "")
        self.cb_inq.pack(side="left", padx=6)

        tk.Label(toolbar, text="Stazione:", font=FONT, fg=TEXT_SUB, bg=PANEL).pack(side="left", padx=(14,0))
        staz_vals = ["Tutte"] + [f"{r['id_stazione']} – {r['area_interessata']}" for r in staz_rows]
        self.cb_staz = combo(toolbar, staz_vals, width=22)
        self.cb_staz.set("Tutte")
        self.cb_staz.pack(side="left", padx=6)

        tk.Label(toolbar, text="Da:", font=FONT, fg=TEXT_SUB, bg=PANEL).pack(side="left", padx=(14,0))
        _, self.e_da = entry(toolbar, width=11)
        toolbar.winfo_children()[-1].pack(side="left", padx=4)

        tk.Label(toolbar, text="A:", font=FONT, fg=TEXT_SUB, bg=PANEL).pack(side="left")
        _, self.e_a = entry(toolbar, width=11)
        toolbar.winfo_children()[-1].pack(side="left", padx=4)

        
        btn_bar = panel(self, padx=16, pady=6)
        btn_bar.pack(fill="x", padx=16, pady=0)

        self._chart_btns = {}
        chart_types = [
            ("Andamento temporale",   "tempo"),
            ("Confronto stazioni",    "barre"),
            ("Distribuzione (boxplot)","boxplot"),
            ("Mappa termica mensile", "heatmap"),
        ]
        for label_t, key in chart_types:
            b = btn(btn_bar, label_t,
                    lambda k=key: self._plot(k),
                    bg=BG, fg=TEXT,
                    pad=(12,6))
            b.config(relief="solid", bd=1, highlightbackground=BORDER)
            b.pack(side="left", padx=4)
            self._chart_btns[key] = b

        separator(self, color=BORDER).pack(fill="x", padx=16, pady=6)

        
        self.chart_area = panel(self, padx=8, pady=8)
        self.chart_area.pack(fill="both", expand=True, padx=16, pady=(0,16))
        tk.Label(self.chart_area,
                 text="Seleziona un tipo di grafico dalla barra sopra",
                 font=FONT, fg=TEXT_SUB, bg=PANEL).pack(expand=True)

    def _clear(self):
        if self._canvas:
            try: self._canvas.get_tk_widget().destroy()
            except: pass
        for w in self.chart_area.winfo_children():
            w.destroy()

    def _base_params(self):
        inq  = self.cb_inq.get()
        staz = self.cb_staz.get()
        sid  = None if staz in ("Tutte","") else int(staz.split("–")[0].strip())
        da   = self.e_da.get().strip() or None
        a    = self.e_a.get().strip()  or None
        return inq, sid, da, a

    def _where(self, params, alias_m="m"):
        inq, sid, da, a = params
        w, p = [], []
        w.append(f"{alias_m}.inquinante=%s"); p.append(inq)
        if sid: w.append(f"{alias_m}.id_stazione=%s"); p.append(sid)
        if da:  w.append(f"{alias_m}.data_rilevazione>=%s"); p.append(da)
        if a:   w.append(f"{alias_m}.data_rilevazione<=%s"); p.append(a)
        return " AND ".join(w), p

    def _plot(self, kind):
        
        for k, b in self._chart_btns.items():
            b.config(bg=ACCENT if k==kind else BG,
                     fg="white" if k==kind else TEXT)
        params = self._base_params()
        inq = params[0]
        self._clear()

        if kind == "tempo":      self._plot_tempo(params, inq)
        elif kind == "barre":    self._plot_barre(params, inq)
        elif kind == "boxplot":  self._plot_box(params, inq)
        elif kind == "heatmap":  self._plot_heat(params, inq)

    def _embed(self, fig):
        matplotlib_fig()
        fig.patch.set_facecolor(PANEL)
        c = FigureCanvasTkAgg(fig, self.chart_area)
        c.get_tk_widget().pack(fill="both", expand=True)
        c.draw(); self._canvas = c

    def _plot_tempo(self, params, inq):
        w, p = self._where(params)
        rows = self.db.q(
            f"SELECT m.data_rilevazione d, AVG(m.valore) v "
            f"FROM misurazioni m WHERE {w} GROUP BY d ORDER BY d", p)
        if not rows: messagebox.showinfo("Info","Nessun dato."); return
        import numpy as np
        dates = [r["d"] for r in rows]
        vals  = [r["v"] for r in rows]
        limite = LIMITI.get(inq, {}).get("valore")

        fig, ax = plt.subplots(figsize=(9,3.8))
        ax.plot(dates, vals, color=ACCENT, linewidth=1.2, alpha=0.6, label=inq)
        ax.fill_between(dates, vals, alpha=0.08, color=ACCENT)
        if len(vals) >= 7:
            mm = np.convolve(vals, np.ones(7)/7, mode='valid')
            ax.plot(dates[3:-3], mm, color=ACCENT, linewidth=2.2, label="Media 7gg")
        if limite:
            ax.axhline(limite, color=DANGER, linestyle="--", linewidth=1.3,
                       label=f"Limite ({limite} {LIMITI[inq]['unita']})")
        ax.set_title(f"Andamento temporale — {inq}", fontsize=12, fontweight="bold")
        ax.set_ylabel(LIMITI.get(inq,{}).get("unita","µg/m³"))
        ax.legend(fontsize=8); ax.grid(True, alpha=0.4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
        fig.tight_layout(pad=1.2); self._embed(fig)

    def _plot_barre(self, params, inq):
        inq, _, da, a = params
        q = ("SELECT s.area_interessata zona, AVG(m.valore) media "
             "FROM misurazioni m JOIN stazioni s ON m.id_stazione=s.id_stazione "
             "WHERE m.inquinante=%s")
        p = [inq]
        if da: q += " AND m.data_rilevazione>=%s"; p.append(da)
        if a:  q += " AND m.data_rilevazione<=%s"; p.append(a)
        q += " GROUP BY zona ORDER BY media DESC"
        rows = self.db.q(q, p)
        if not rows: messagebox.showinfo("Info","Nessun dato."); return

        labels = [r["zona"].replace("Milano - ","") for r in rows]
        values = [r["media"] for r in rows]
        limite = LIMITI.get(inq,{}).get("valore")
        colors = [DANGER if limite and v > limite else ACCENT for v in values]

        fig, ax = plt.subplots(figsize=(9,3.8))
        bars = ax.bar(labels, values, color=colors, alpha=0.85, width=0.55)
        if limite:
            ax.axhline(limite, color=DANGER, linestyle="--", linewidth=1.3,
                       label=f"Limite ({limite})")
            ax.legend(fontsize=8)
        for bar, v in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                    f"{v:.1f}", ha="center", fontsize=8.5, color=TEXT_SUB)
        ax.set_title(f"Confronto stazioni — {inq}", fontsize=12, fontweight="bold")
        ax.set_ylabel(LIMITI.get(inq,{}).get("unita","µg/m³"))
        ax.grid(True, axis="y", alpha=0.4)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=20, ha="right")
        fig.tight_layout(pad=1.2); self._embed(fig)

    def _plot_box(self, params, inq):
        inq, _, da, a = params
        q = ("SELECT s.area_interessata zona, m.valore "
             "FROM misurazioni m JOIN stazioni s ON m.id_stazione=s.id_stazione "
             "WHERE m.inquinante=%s")
        p = [inq]
        if da: q += " AND m.data_rilevazione>=%s"; p.append(da)
        if a:  q += " AND m.data_rilevazione<=%s"; p.append(a)
        rows = self.db.q(q, p)
        if not rows: messagebox.showinfo("Info","Nessun dato."); return
        from collections import defaultdict
        dm = defaultdict(list)
        for r in rows:
            dm[r["zona"].replace("Milano - ","")].append(r["valore"])

        fig, ax = plt.subplots(figsize=(9,3.8))
        bp = ax.boxplot(list(dm.values()), labels=list(dm.keys()),
                        patch_artist=True, notch=False, widths=0.5)
        for patch, col in zip(bp["boxes"], PLT_PALETTE):
            patch.set_facecolor(col); patch.set_alpha(0.6)
        for elem in ["whiskers","medians","caps"]:
            for line in bp[elem]: line.set_color(TEXT_SUB)
        limite = LIMITI.get(inq,{}).get("valore")
        if limite:
            ax.axhline(limite, color=DANGER, linestyle="--", linewidth=1.3,
                       label=f"Limite ({limite})")
            ax.legend(fontsize=8)
        ax.set_title(f"Distribuzione {inq} per stazione", fontsize=12, fontweight="bold")
        ax.set_ylabel(LIMITI.get(inq,{}).get("unita","µg/m³"))
        ax.grid(True, axis="y", alpha=0.4)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=20, ha="right")
        fig.tight_layout(pad=1.2); self._embed(fig)

    def _plot_heat(self, params, inq):
        inq, sid, da, a = params
        q = ("SELECT MONTH(data_rilevazione) mese, "
             "DAYOFWEEK(data_rilevazione) dow, AVG(valore) v "
             "FROM misurazioni WHERE inquinante=%s")
        p = [inq]
        if sid: q += " AND id_stazione=%s"; p.append(sid)
        if da:  q += " AND data_rilevazione>=%s"; p.append(da)
        if a:   q += " AND data_rilevazione<=%s"; p.append(a)
        q += " GROUP BY mese, dow"
        rows = self.db.q(q, p)
        if not rows: messagebox.showinfo("Info","Nessun dato."); return

        import numpy as np
        mat = np.full((12,7), float("nan"))
        for r in rows:
            mat[int(r["mese"])-1][int(r["dow"])-1] = r["v"]

        fig, ax = plt.subplots(figsize=(9,3.8))
        im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", interpolation="nearest")
        fig.colorbar(im, ax=ax, label=LIMITI.get(inq,{}).get("unita","µg/m³"))
        mesi   = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
        giorni = ["Dom","Lun","Mar","Mer","Gio","Ven","Sab"]
        ax.set_yticks(range(12)); ax.set_yticklabels(mesi, fontsize=8)
        ax.set_xticks(range(7));  ax.set_xticklabels(giorni, fontsize=8)
        ax.set_title(f"Mappa termica {inq} — Mese × Giorno settimana",
                     fontsize=12, fontweight="bold")
        fig.tight_layout(pad=1.2); self._embed(fig)


# ─────────────────────────────────────────────────────────────────────────────
# SCHERMATA 4 — SUPERAMENTI
# ─────────────────────────────────────────────────────────────────────────────
class SuperamentiView(tk.Frame):
    def __init__(self, parent, db: DB):
        super().__init__(parent, bg=BG)
        self.db = db
        self._build()
        self._refresh()

    def _build(self):
       
        top = tk.Frame(self, bg=BG, padx=24, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="Superamenti Limiti Normativi",
                 font=FONT_TITLE, fg=TEXT, bg=BG).pack(side="left")

        info = panel(self, padx=16, pady=10)
        info.pack(fill="x", padx=16, pady=(0,6))
        tk.Label(info, text="Limiti di riferimento utilizzati (Direttiva UE 2008/50/CE):",
                 font=FONT_BOLD, fg=TEXT, bg=PANEL).pack(anchor="w")
        lim_frame = tk.Frame(info, bg=PANEL)
        lim_frame.pack(fill="x", pady=4)
        for i, (k, v) in enumerate(LIMITI.items()):
            c = tk.Frame(lim_frame, bg=PANEL, padx=8, pady=4,
                         relief="solid", bd=1, highlightbackground=BORDER)
            c.grid(row=0, column=i, padx=4, sticky="ew")
            lim_frame.columnconfigure(i, weight=1)
            col = PLT_PALETTE[i % len(PLT_PALETTE)]
            tk.Frame(c, bg=col, height=3).pack(fill="x", pady=(0,4))
            tk.Label(c, text=k, font=FONT_BOLD, fg=col, bg=PANEL).pack()
            tk.Label(c, text=f"{v['valore']} {v['unita']}", font=FONT_SMALL, fg=TEXT, bg=PANEL).pack()
            tk.Label(c, text=v["tipo"], font=FONT_SMALL, fg=TEXT_SUB, bg=PANEL).pack()

    
        flt = panel(self, padx=14, pady=8)
        flt.pack(fill="x", padx=16, pady=0)
        tk.Label(flt, text="Inquinante:", font=FONT, fg=TEXT_SUB, bg=PANEL).pack(side="left")
        self.cb_inq = combo(flt, ["Tutti"]+list(LIMITI.keys()), width=12)
        self.cb_inq.set("Tutti"); self.cb_inq.pack(side="left", padx=6)
        tk.Label(flt, text="Stazione:", font=FONT, fg=TEXT_SUB, bg=PANEL).pack(side="left", padx=(14,0))
        staz_rows = self.db.q("SELECT id_stazione, area_interessata FROM stazioni ORDER BY id_stazione")
        staz_vals = ["Tutte"]+[f"{r['id_stazione']} – {r['area_interessata']}" for r in staz_rows]
        self.cb_staz = combo(flt, staz_vals, width=24)
        self.cb_staz.set("Tutte"); self.cb_staz.pack(side="left", padx=6)
        btn(flt, "Filtra", self._refresh, bg=ACCENT).pack(side="left", padx=8)
        self.lbl_tot = tk.Label(flt, text="", font=FONT_BOLD, fg=DANGER, bg=PANEL)
        self.lbl_tot.pack(side="right", padx=8)

       
        tree_panel = panel(self, padx=8, pady=8)
        tree_panel.pack(fill="both", expand=True, padx=16, pady=8)

        cols = ("Data","Stazione","Inquinante","Valore","Limite","Unità","Eccesso %","Tipo media")
        self.tree = ttk.Treeview(tree_panel, columns=cols, show="headings",
                                  style="Light.Treeview", height=16)
        widths = [100,195,90,70,65,65,80,120]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        self.tree.tag_configure("alto",   background="#FFEBEE", foreground=DANGER)
        self.tree.tag_configure("medio",  background="#FFF8E1", foreground=WARNING_COL)

        sb = ttk.Scrollbar(tree_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        inq_flt  = self.cb_inq.get()
        staz_flt = self.cb_staz.get()
        targets = [(k,v) for k,v in LIMITI.items()
                   if inq_flt in ("Tutti", k)]
        all_rows = []
        for inq_id, lim in targets:
            q = ("SELECT m.data_rilevazione, s.area_interessata, m.inquinante, m.valore "
                 "FROM misurazioni m JOIN stazioni s ON m.id_stazione=s.id_stazione "
                 "WHERE m.inquinante=%s AND m.valore>%s")
            p = [inq_id, lim["valore"]]
            if staz_flt not in ("Tutte",""):
                q += " AND m.id_stazione=%s"
                p.append(int(staz_flt.split("–")[0].strip()))
            rows = self.db.q(q+" ORDER BY m.data_rilevazione DESC", p)
            for r in rows:
                d = r["data_rilevazione"]
                d_str = d.strftime("%Y-%m-%d") if hasattr(d,"strftime") else str(d)
                pct = (r["valore"]-lim["valore"])/lim["valore"]*100
                all_rows.append((d_str, r["area_interessata"], r["inquinante"],
                                 r["valore"], lim["valore"], lim["unita"],
                                 pct, lim["tipo"]))

        all_rows.sort(key=lambda x: x[0], reverse=True)
        for r in all_rows:
            tag = "alto" if r[6] > 50 else "medio"
            self.tree.insert("","end",
                             values=(r[0], r[1], r[2],
                                     f"{r[3]:.2f}", f"{r[4]}", r[5],
                                     f"+{r[6]:.1f}%", r[7]),
                             tags=(tag,))
        self.lbl_tot.config(text=f"Totale: {len(all_rows)} superamenti")


# ─────────────────────────────────────────────────────────────────────────────
# SCHERMATA 5 — STAZIONI
# ─────────────────────────────────────────────────────────────────────────────
class StazioniView(tk.Frame):
    def __init__(self, parent, db: DB):
        super().__init__(parent, bg=BG)
        self.db = db
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG, padx=24, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="Stazioni di Monitoraggio",
                 font=FONT_TITLE, fg=TEXT, bg=BG).pack(side="left")

        try:
            stazioni = self.db.q(
                "SELECT s.id_stazione, s.area_interessata, s.latitudine, s.longitudine, "
                "COUNT(m.id_misurazione) n "
                "FROM stazioni s LEFT JOIN misurazioni m ON s.id_stazione=m.id_stazione "
                "GROUP BY s.id_stazione,s.area_interessata,s.latitudine,s.longitudine "
                "ORDER BY s.id_stazione")
        except:
            stazioni = []

        
        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=20, pady=10)
        for col in range(3): grid.columnconfigure(col, weight=1)

        for i, s in enumerate(stazioni):
            row_i, col_i = divmod(i, 3)
            color = PLT_PALETTE[i % len(PLT_PALETTE)]
            card = tk.Frame(grid, bg=PANEL, relief="solid", bd=1,
                            highlightbackground=BORDER, padx=0, pady=0)
            card.grid(row=row_i, column=col_i, padx=10, pady=8, sticky="nsew")
            grid.rowconfigure(row_i, weight=1)

            
            tk.Frame(card, bg=color, height=5).pack(fill="x")

            body = tk.Frame(card, bg=PANEL, padx=16, pady=12)
            body.pack(fill="both", expand=True)

            tk.Label(body, text=f"Stazione {s['id_stazione']}",
                     font=("Segoe UI", 10, "bold"), fg=color, bg=PANEL).pack(anchor="w")
            tk.Label(body, text=s["area_interessata"],
                     font=("Segoe UI", 11, "bold"), fg=TEXT, bg=PANEL).pack(anchor="w")
            tk.Label(body, text=f"📌  {s['latitudine']:.4f}°N,  {s['longitudine']:.4f}°E",
                     font=FONT_SMALL, fg=TEXT_SUB, bg=PANEL).pack(anchor="w", pady=(6,0))

            separator(body, color=BORDER).pack(fill="x", pady=6)

            stat_row = tk.Frame(body, bg=PANEL)
            stat_row.pack(fill="x")
            self._stat_box(stat_row, str(s["n"]), "misurazioni", color)

            
            try:
                inq_rows = self.db.q(
                    "SELECT inquinante, COUNT(*) n FROM misurazioni "
                    "WHERE id_stazione=%s GROUP BY inquinante ORDER BY n DESC",
                    (s["id_stazione"],))
                if inq_rows:
                    matplotlib_fig()
                    fig, ax = plt.subplots(figsize=(2.6, 1.4))
                    ax.bar([r["inquinante"] for r in inq_rows],
                           [r["n"] for r in inq_rows],
                           color=color, alpha=0.75)
                    ax.set_yticks([])
                    ax.tick_params(axis="x", labelsize=6, rotation=30)
                    ax.set_title("Misurazioni/inquinante", fontsize=6, color=TEXT_SUB)
                    fig.tight_layout(pad=0.4)
                    c = FigureCanvasTkAgg(fig, body)
                    c.get_tk_widget().pack(fill="x", pady=(4,0))
                    c.draw()
            except: pass

    def _stat_box(self, parent, value, label_text, color):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(side="left", padx=6)
        tk.Label(f, text=value, font=("Segoe UI",16,"bold"), fg=color, bg=PANEL).pack()
        tk.Label(f, text=label_text, font=FONT_SMALL, fg=TEXT_SUB, bg=PANEL).pack()


# ─────────────────────────────────────────────────────────────────────────────
# APPLICAZIONE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────
class AireApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AIRE — Qualità dell'Aria a Milano")
        self.geometry("1300x800")
        self.minsize(1100, 680)
        self.configure(bg=TOPBAR_BG)

        self.db = DB()
        self._views: dict[str, tk.Frame] = {}
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        
        topbar = tk.Frame(self, bg=TOPBAR_BG, pady=0)
        topbar.pack(fill="x", side="top")

        
        logo = tk.Frame(topbar, bg=TOPBAR_BG, padx=18)
        logo.pack(side="left")
        tk.Label(logo, text="🌫", font=("Segoe UI", 18), bg=TOPBAR_BG,
                 fg="white").pack(side="left")
        tk.Label(logo, text="  AIRE", font=("Segoe UI", 13, "bold"),
                 bg=TOPBAR_BG, fg="white").pack(side="left")

        
        tk.Frame(topbar, width=1).pack(side="left", fill="y", pady=6)

        
        tabs = [
            ("home",         "Dashboard",        "▤"),
            ("misurazioni",  "Misurazioni",       "≡"),
            ("grafici",      "Grafici",           "◈"),
            ("superamenti",  "Superamenti",       "⚠"),
            ("stazioni",     "Stazioni",          "◉"),
        ]
        self.tabbar = TabBar(topbar, tabs, self._show)
        self.tabbar.pack(side="left")

        
        tk.Label(topbar, text="Generation Italy",
                 font=FONT_SMALL, fg="#B0C4DE", bg=TOPBAR_BG,
                 padx=16).pack(side="right", anchor="center")

        
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True)

        
        self.tabbar.set_active("home")

    def _show(self, key):
        if key not in self._views:
            cls_map = {
                "home":        HomeView,
                "misurazioni": MisurazioniView,
                "grafici":     GraficiView,
                "superamenti": SuperamentiView,
                "stazioni":    StazioniView,
            }
            view = cls_map[key](self.content, self.db)
            view.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._views[key] = view
        self._views[key].lift()

    def _on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = AireApp()
    app.mainloop()