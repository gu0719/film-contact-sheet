from __future__ import annotations

from collections import Counter

from film_contact_sheet.models import Frame


def sort_frames(frames: list[Frame]) -> list[Frame]:
    numbered = [frame for frame in frames if frame.edge_number is not None]
    missing = [frame for frame in frames if frame.edge_number is None]
    numbered.sort(key=lambda frame: (frame.edge_number, frame.filename))
    missing.sort(key=lambda frame: frame.filename)
    return numbered + missing


def apply_warnings(frames: list[Frame]) -> None:
    counts = Counter(frame.edge_number for frame in frames if frame.edge_number is not None)
    for index, frame in enumerate(frames):
        reasons = []
        if frame.edge_number is None:
            reasons.append("未识别")
        else:
            if counts[frame.edge_number] > 1:
                reasons.append("序号重复")
            if index > 0:
                previous = frames[index - 1].edge_number
                if previous is not None and frame.edge_number <= previous:
                    reasons.append("序号未递增")
        frame.warning = "、".join(reasons)
