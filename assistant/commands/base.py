import logging

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify

from ..abc import MixinMeta
from ..common.utils import get_attachments
from ..models import READ_EXTENSIONS

log = logging.getLogger("red.vrt.assistant.base")


class Base(MixinMeta):
    @commands.command(name="chat")
    @commands.guild_only()
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def ask_question(self, ctx: commands.Context, *, question: str):
        """Ask [botname] a question!"""
        conf = self.db.get_conf(ctx.guild)
        if not conf.api_key:
            return await ctx.send("This command requires an API key from OpenAI to be configured!")
        async with ctx.typing():
            if attachments := get_attachments(ctx.message):
                for i in attachments:
                    if not any(i.filename.lower().endswith(ext) for ext in READ_EXTENSIONS):
                        continue
                    text = await i.read()
                    question += f"\n\nUploaded [{i.filename}]: {text.decode()}"
            try:
                reply = await self.get_chat_response(question, ctx.author, ctx.channel, conf)
                if len(reply) < 2000:
                    return await ctx.reply(reply, mention_author=conf.mention)

                embeds = [
                    discord.Embed(description=p)
                    for p in pagify(reply, page_length=4000, delims=("```", "\n"))
                ]
                await ctx.reply(embeds=embeds, mention_author=conf.mention)

            except Exception as e:
                await ctx.send(f"**Error**\n```py\n{e}\n```")
                log.error("Chat command failed", exc_info=e)

    @commands.command(name="convostats")
    @commands.guild_only()
    async def token_count(self, ctx: commands.Context, *, user: discord.Member = None):
        """Check the token and message count of yourself or another user's conversation"""
        if not user:
            user = ctx.author
        conf = self.db.get_conf(ctx.guild)
        conversation = self.chats.get_conversation(user)
        messages = len(conversation.messages)
        embed = discord.Embed(
            title="Token Usage",
            description=(
                f"`Messages: `{messages}\n"
                f"`Tokens:   `{conversation.user_token_count()}\n"
                f"`Expired:  `{conversation.is_expired(conf)}"
            ),
            color=user.color,
        )
        await ctx.send(embed=embed)

    @commands.command(name="clearconvo")
    @commands.guild_only()
    async def clear_convo(self, ctx: commands.Context):
        """Reset your conversation"""
        conversation = self.chats.get_conversation(ctx.author)
        conversation.reset()
        await ctx.tick()
