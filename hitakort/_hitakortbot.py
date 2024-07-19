# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (c) 2024 Nachtalb
import logging
from functools import reduce
from io import BytesIO
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, ExtBot, MessageHandler, filters

from hitakort._hitakort import HitaKort
from hitakort.defaults import CWD, HIT_REGEX
from hitakort.utils import sel


class HitaKortBot:
    def __init__(
        self,
        admins: list[int | str] = [],
        lock_to_admins: bool = True,
        local_mode: bool = False,
        hitakort_path: Path = CWD,
    ):
        self.logger = logging.getLogger(__name__)
        self.local_mode = local_mode
        self.admins = [int(admin) for admin in admins if isinstance(admin, int) or admin.isdigit()]
        self.lock_to_admins = lock_to_admins

        self.bot: ExtBot = None  # type: ignore[type-arg, assignment]
        self.hitakort_path = hitakort_path / "users"
        self.hitakorts: dict[int, HitaKort] = {}

    def setup_hooks(self, application: Application) -> None:  # type: ignore[type-arg]
        hit_filter = filters.Regex(HIT_REGEX)
        admin_filter = None

        if self.lock_to_admins and self.admins:
            user_filters = [filters.User(user) for user in self.admins]
            multi_user_filter = user_filters[0]
            if len(user_filters) > 1:
                multi_user_filter = reduce(lambda x, y: x | y, user_filters)  # type: ignore[arg-type, return-value]

            admin_filter = filters.ChatType.PRIVATE & multi_user_filter

        application.add_handler(CommandHandler("start", self.start, filters=admin_filter, block=False))
        application.add_handler(CommandHandler("size", self.size, filters=admin_filter, block=False))
        application.add_handler(CommandHandler("image", self.heatmap, filters=admin_filter, block=False))
        application.add_handler(CommandHandler("reset", self.reset, filters=admin_filter, block=False))
        application.add_handler(
            MessageHandler(admin_filter & hit_filter if admin_filter else hit_filter, self.add_hit, block=False)
        )
        application.add_handler(
            MessageHandler(
                admin_filter & filters.TEXT if admin_filter else filters.TEXT, self.wrong_format, block=False
            )
        )
        application.add_handler(
            MessageHandler(admin_filter & filters.ALL if admin_filter else filters.ALL, self.not_supported, block=False)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received start command from: {update.effective_user.full_name}")

        text = """<b>HitaKort Bot</b>

        👋 Hello! I'm HitaKort Bot. <i>Hita</i> is Old Norse for <code>heat</code> and <i>Kort</i> is Old Norse for <code>Map</code>. Giving me hits on a 6x6 grid I will return a heatmap where the hits are located most frequently.

        🎉 First send me the grid size you want with /size &lt;num&gt;. Then send me a hit in the format of ROW COLUMN where ROW is a letter and COLUMN is a number. For example: A1, B2, C3, etc.
        """

        await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)

    async def size(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received size command from: {update.effective_user.full_name}")

        user_id = update.effective_user.id
        if user_id in self.hitakorts:
            text = """<b>Grid Size Already Set</b>

            🤔 You have already set the grid size. If you want to reset the heatmap, use /reset.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return

        if not context.args:
            text = """<b>Set Grid Size</b>

            🤔 You need to specify the grid size with /size &lt;num&gt;. For example: /size 6.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return

        try:
            size = int(context.args[0])
            if size < 2:
                raise ValueError
        except ValueError:
            text = """<b>Invalid Grid Size</b>

            🤔 The grid size must be an integer greater than 1.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            self.logger.error(f"Failed to parse grid size: {e}")
            text = """<b>Failed to set Grid Size</b>

            🤔 An error occurred while setting the grid size.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return

        self.hitakorts[user_id] = HitaKort(self.hitakort_path / (str(user_id) + ".json"), size)

        text = f"""<b>Grid Size Set</b>

        🎉 The grid size has been set to {size}. You can now start adding hits to the grid.
        """
        await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)

    async def heatmap(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received heatmap command from: {update.effective_user.full_name}")

        user_id = update.effective_user.id
        if user_id not in self.hitakorts:
            text = """<b>Grid Size Not Set</b>

            🤔 You need to set the grid size first with /size &lt;num&gt;.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return

        hitakort = self.hitakorts[user_id]
        image = hitakort.generate_heatmap_image()

        bytes = BytesIO()
        image.save(bytes, format="PNG")
        bytes.seek(0)
        await update.message.reply_photo(bytes, filename="heatmap.png")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received reset command from: {update.effective_user.full_name}")

        user_id = update.effective_user.id
        if user_id not in self.hitakorts:
            text = """<b>Grid Size Not Set</b>

            🤔 You need to set the grid size first with /size &lt;num&gt;.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return

        self.hitakorts[user_id].file_path.unlink(missing_ok=True)
        del self.hitakorts[user_id]

        text = """<b>Grid Reset</b>

        🎉 The grid has been reset. You can now set the grid size with /size &lt;num&gt;.
        """
        await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)

    async def add_hit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user or not update.message.text:
            return

        self.logger.info(f"Received hit from: {update.effective_user.full_name}")

        user_id = update.effective_user.id
        if user_id not in self.hitakorts:
            text = """<b>Grid Size Not Set</b>

            🤔 You need to set the grid size first with /size &lt;num&gt;.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
            return

        hitakort = self.hitakorts[user_id]
        hit = update.message.text.upper()
        try:
            hitakort.input_hit(hit)

            text = f"""<b>Hit Added</b>

            🎉 The hit {hit} has been added to the grid. You can view the heatmap with /image.
            """

            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)
        except ValueError:
            text = """<b>Invalid Hit</b>

            🤔 You need to send me a valid hit in the format of ROW COLUMN where ROW is a letter and COLUMN is a number. For example: A1, B2, C3, etc.
            """
            await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)

    async def wrong_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received wrong format message from: {update.effective_user.full_name}")

        text = """<b>Wrong format</b>

        🤔 You need to send me a valid hit in the format of ROW COLUMN where ROW is a letter and COLUMN is a number. For example: A1, B2, C3, etc.
        """

        await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)

    async def not_supported(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        self.logger.info(f"Received not supported message from: {update.effective_user.full_name}")

        text = """<b>Not supported</b>

        🤔 I'm sorry, but I don't support this type of message.
        """

        await update.message.reply_text(sel(text), parse_mode=ParseMode.HTML)

    async def post_init(self, app: Application) -> None:  # type: ignore[type-arg]
        self.app = app
        self.bot = app.bot

        await self.bot.set_my_commands(
            [
                ("start", "Start the bot"),
                ("size", "Set the grid size"),
                ("image", "Get the heatmap image"),
                ("reset", "Reset the heatmap"),
            ]
        )

        for admin in self.admins:
            try:
                await self.bot.send_message(admin, "Bot started!")
            except BadRequest as e:
                self.logger.error(f"Failed to send message to admin: {admin}, error: {e}")

        for file in self.hitakort_path.glob("*.json"):
            user_id = int(file.stem)
            self.hitakorts[user_id] = HitaKort(file)

    async def post_stop(self, app: Application) -> None:  # type: ignore[type-arg]
        for admin in self.admins:
            try:
                await self.bot.send_message(admin, "Bot stopped!")
            except BadRequest as e:
                self.logger.error(f"Failed to send message to admin: {admin}, error: {e}")
