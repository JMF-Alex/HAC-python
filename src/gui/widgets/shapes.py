import tkinter as tk


def rounded_rect(canvas, x1, y1, x2, y2, radius, **options):
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = (
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    )
    return canvas.create_polygon(points, smooth=True, **options)


class CanvasWidget(tk.Canvas):
    def __init__(self, parent, width, height, **options):
        super().__init__(
            parent, width=width, height=height, bg=parent.cget("bg"), highlightthickness=0, bd=0, **options,
        )
        self.bind("<Configure>", lambda _e: self.redraw(), add="+")

    def redraw(self) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width < 2 or height < 2:
            width, height = int(self.cget("width")), int(self.cget("height"))
        self.delete("all")
        self.draw(width, height)

    def draw(self, width: int, height: int) -> None:
        raise NotImplementedError


class RoundedFrame(tk.Frame):
    def __init__(self, parent, fill, outline=None, radius=12, **options):
        outer = parent.cget("bg")
        super().__init__(parent, bg=fill, **options)
        self._fill, self._outline, self._radius = fill, outline, radius
        self._canvas = tk.Canvas(self, bg=outer, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        tk.Misc.lower(self._canvas)
        self._canvas.bind("<Configure>", lambda _e: self._draw())

    @property
    def canvas(self):
        return self._canvas

    def set_colors(self, fill=None, outline=None) -> None:
        if fill is not None:
            self._fill = fill
        self._outline = outline
        self._draw()

    def _draw(self) -> None:
        canvas = self._canvas
        width, height = canvas.winfo_width(), canvas.winfo_height()
        canvas.delete("all")
        if width < 2 or height < 2:
            return
        rounded_rect(
            canvas, 0, 0, width - 1, height - 1, self._radius,
            fill=self._fill, outline=self._outline or self._fill,
        )
