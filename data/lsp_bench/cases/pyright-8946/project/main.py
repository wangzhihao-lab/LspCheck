from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime

import os
from multiprocessing import Pool
from typing import Callable


def execute_shell_commands(
    dates: list[datetime.date],
    cmd: Callable[[datetime.date], str],
    workers: int = 1,
) -> list[tuple[int, datetime.date]]:
    with Pool(workers) as po:
        exit_codes = po.map(os.system, [cmd(d) for d in dates])
        return [ret for ret in zip(exit_codes, dates) if ret[0] != 0]


