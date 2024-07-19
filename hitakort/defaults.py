# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (c) 2024 Nachtalb
from pathlib import Path

CWD = Path().absolute()
TG_BASE_URL = "https://api.telegram.org/bot"

TG_MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024  # 20 MB
# TG_LOCAL_MAX_DOWNLOAD_SIZE  # no size limit in local mode
