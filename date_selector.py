import tkinter as tk
from tkcalendar import Calendar
from datetime import date

class DateSelector:
    def __init__(self, callback):
        self.callback = callback
        self.root = tk.Tk()
        self.root.title("Seleccionar Rango de Fechas - Klaviyo Metrics All-in-One v6")
        self.setup_ui()
        self.root.result = None
        self.root.mainloop()

    def setup_ui(self):
        # Configurar el tamaño y posición de la ventana
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = max(int(screen_width * 0.5), 800)
        window_height = max(int(screen_height * 0.4), 400)
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.after_ids = []

        # Añadir el nombre de la aplicación
        app_name_label = tk.Label(
            self.root,
            text="Klaviyo Metrics All-in-One",
            font=("Fira Sans", 16, "bold"),
            fg="#23376D",
            pady=10
        )
        app_name_label.place(relx=0.5, rely=0.1, anchor="center")

        # Configurar fechas por defecto
        today = date.today()
        current_year = today.year
        current_month = today.month
        current_day = today.day

        # Frame principal para los calendarios
        frame = tk.Frame(self.root)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Calendario de fecha inicial
        frame_start = tk.Frame(frame)
        frame_start.pack(side=tk.LEFT, padx=30)
        tk.Label(frame_start, text="Fecha Inicial:", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack()
        self.cal_start = Calendar(frame_start, selectmode="day", year=current_year, month=current_month, day=current_day, 
                                 date_pattern="yyyy-mm-dd", firstweekday="sunday", showweeknumbers=False)
        self.cal_start.pack()

        # Calendario de fecha final
        frame_end = tk.Frame(frame)
        frame_end.pack(side=tk.LEFT, padx=30)
        tk.Label(frame_end, text="Fecha Final:", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack()
        self.cal_end = Calendar(frame_end, selectmode="day", year=current_year, month=current_month, day=current_day, 
                               date_pattern="yyyy-mm-dd", firstweekday="sunday", showweeknumbers=False)
        self.cal_end.pack()

        # Botón para confirmar selección
        tk.Button(self.root, text="Confirmar", command=self.obtener_fechas, bg="#23376D", fg="white", 
                  activebackground="#3A4F9A", activeforeground="white", font=("TkDefaultFont", 10, "bold")).place(relx=0.5, rely=0.9, anchor="center")
        self.root.protocol("WM_DELETE_WINDOW", lambda: [self.root.quit(), self.root.destroy()])

    def obtener_fechas(self):
        start_date = self.cal_start.get_date()
        end_date = self.cal_end.get_date()
        self.root.result = (start_date, end_date)
        for after_id in list(self.root.after_ids):
            self.root.after_cancel(after_id)
        self.root.quit()
        self.root.destroy()
        self.callback(start_date, end_date)

    def get_result(self):
        return self.root.result