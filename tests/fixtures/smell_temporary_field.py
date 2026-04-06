"""Fixture: Temporary Field."""


class Report:
    def __init__(self, title):
        self.title = title
        self.pages = []

    def generate_pdf(self):
        self.pdf_data = self._render()
        self.pdf_size = len(self.pdf_data)
        return self.pdf_data

    def generate_csv(self):
        self.csv_data = self._export()
        return self.csv_data

    def _render(self):
        return b"PDF content"

    def _export(self):
        return "csv,content"
