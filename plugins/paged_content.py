# -*- coding: utf-8 -*-
import math
import random
import time
from collections import deque
from spanky.hook2 import Hook, EventType

LARROW = "⬅"
RARROW = "➡"
RANDOM = "🔢"
TIMEOUT = 2
# elements = deque(maxlen=10)

hook = Hook("paged_content")


class element:
    def __init__(
        self,
        text_list,
        send_func,
        description="",
        max_lines=10,
        max_line_len=200,
        no_timeout=False,
        with_quotes=True,
        line_separator="\n",
    ):
        self.max_lines = max_lines
        self.crt_idx = 0
        self.description = description

        self.time = time.time()
        self.no_timeout = no_timeout

        self.send = send_func
        self.with_quotes = with_quotes

        self.line_separator = line_separator

        self.parsed_lines = []
        for line in text_list:
            if len(line) > max_line_len:
                while len(line) >= max_line_len:
                    self.parsed_lines.append(line[:max_line_len])
                    line = line[max_line_len:]
            else:
                self.parsed_lines.append(line)

        self.id = None

    def register(self, msg_id):
        add_handler(msg_id, self)

    async def get_crt_page(self):
        tlist = self.parsed_lines[self.crt_idx : self.crt_idx + self.max_lines]

        with_arrows = False
        page_header = self.description + "\n"
        if len(self.parsed_lines) > self.max_lines:
            with_arrows = True
            page_header += "Page %d/%d\n" % (
                self.crt_idx / self.max_lines + 1,
                math.ceil(len(self.parsed_lines) / self.max_lines),
            )

        output = ""
        if self.with_quotes:
            output = page_header + "```" + self.line_separator.join(tlist) + "```"
        else:
            output = page_header + self.line_separator.join(tlist)
        msg = await self.send(output)
        self.register(msg.id)

        # Add arrow emojis
        if with_arrows:
            await msg.async_add_reaction(LARROW)
            await msg.async_add_reaction(RARROW)
            await msg.async_add_reaction(RANDOM)

    async def get_next_page(self):
        if self.crt_idx + self.max_lines < len(self.parsed_lines):
            self.crt_idx += self.max_lines
        else:
            self.crt_idx = 0

        await self.get_crt_page()

    async def get_prev_page(self):
        if self.crt_idx - self.max_lines >= 0:
            self.crt_idx -= self.max_lines
        else:
            self.crt_idx = (
                len(self.parsed_lines) - len(self.parsed_lines) % self.max_lines - 1
            )

        await self.get_crt_page()

    async def get_random_page(self):
        self.crt_idx = (
            random.randint(0, len(self.parsed_lines) // self.max_lines) * self.max_lines
        )
        await self.get_crt_page()


def add_handler(msg_id: str, content: element):
    async def handler(event):
        if not (
            event.reaction.emoji.name == LARROW
            or event.reaction.emoji.name == RARROW
            or event.reaction.emoji.name == RANDOM
        ):
            return

        await event.msg.async_remove_reaction(event.reaction.emoji.name, event.author)

        # Check timeout
        if not content.no_timeout and time.time() - content.time < TIMEOUT:
            return
        else:
            content.time = time.time()

        if event.reaction.emoji.name == LARROW:
            await content.get_prev_page()

        if event.reaction.emoji.name == RARROW:
            await content.get_next_page()

        if event.reaction.emoji.name == RANDOM:
            await content.get_random_page()

    hook.add_temporary_msg_react(msg_id, handler)
