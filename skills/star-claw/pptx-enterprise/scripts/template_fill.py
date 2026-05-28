#!/usr/bin/env python3
"""Fill a branded .potx/.pptx template in place via python-pptx, preserving masters/theme/fonts."""
import copy
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.text.text import _Paragraph


def _set_paragraph_text(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        paragraph.add_run().text = text


def _fill_text_frame(tf, value) -> None:
    lines = [str(x) for x in value] if isinstance(value, list) else str(value).split("\n")
    lines = lines or [""]
    template_xml = copy.deepcopy(tf.paragraphs[0]._p)
    for p in list(tf.paragraphs[1:]):
        p._p.getparent().remove(p._p)
    _set_paragraph_text(tf.paragraphs[0], lines[0])
    anchor = tf.paragraphs[0]._p
    for line in lines[1:]:
        new_p = copy.deepcopy(template_xml)
        anchor.addnext(new_p)
        anchor = new_p
        _set_paragraph_text(_Paragraph(new_p, tf), line)


def fill(template_path: str, content_path: str, out_path: str) -> None:
    prs = Presentation(template_path)
    content = json.loads(Path(content_path).read_text(encoding="utf-8"))
    by_slide = {int(k): v for k, v in content.get("slides", {}).items()}
    for idx, slide in enumerate(prs.slides):
        payload = by_slide.get(idx, {})
        if not payload:
            continue
        for shape in slide.placeholders:
            if shape.name in payload and shape.has_text_frame:
                _fill_text_frame(shape.text_frame, payload[shape.name])
    prs.save(out_path)
    print(f"wrote {out_path}")


def main() -> None:
    if len(sys.argv) < 4:
        print("usage: template_fill.py <template.pptx|.potx> <content.json> <out.pptx>", file=sys.stderr)
        print('  content.json: {"slides": {"0": {"<placeholder_name>": "value", ...}, ...}}', file=sys.stderr)
        sys.exit(2)
    fill(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
