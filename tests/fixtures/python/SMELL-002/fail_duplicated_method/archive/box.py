"""Archive box."""


class Box:
    def label_for(self, entry):
        from string import capwords as cap

        def clean(raw):
            return cap(raw.strip())

        try:
            part = entry.extra["section"]
        except KeyError as absent:
            part = str(absent)
        return "-".join([entry.code, clean(part)])
