"""Catalog shelf."""


class Shelf:
    def label_for(self, item):
        from string import capwords as titled

        def tidy(text):
            return titled(text.strip())

        try:
            section = item.extra["section"]
        except KeyError as missing:
            section = str(missing)
        return "-".join([item.code, tidy(section)])
