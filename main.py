import os
import asyncio
import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.events import NewMessage
import logging
from animesdb import DBHelper, tables

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s', level=logging.WARNING)

API_ID: int = int(os.getenv("API_ID"))
API_HASH: str = os.getenv("API_HASH")
STRING_SESSION: str = os.environ.get("STRING_SESSION", None)
db = DBHelper(os.getenv("DATABASE_URL"))

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH).start()

if STRING_SESSION is None:
    print("Your string session is:\n" + StringSession.save(client.session))


channels = []
destination = []
reg_exp = ''
not_exist = f'There is no such type in the db\n\nposible:\n{", ".join(tables)}'
error = 'An error has occurred and the items could not be added.'


async def act_list(tipo: str):
    result = db.get_items(tipo)
    lista = [x.att for x in result]
    if tipo == tables[0]:
        animes = lista
        global reg_exp
        if animes:
            reg_exp = '(?i).*(' + "|".join([x.replace(" ", "[\W_]") for x in animes]) + ').*'
        else:
            reg_exp = ''
    elif tipo == tables[1]:
        global channels
        channels = [await client.get_input_entity(x) for x in lista]
    else:
        global destination
        destination = lista

    return result


def filter_type(message: NewMessage):
    if message.input_chat in channels and (message.video or message.document)\
            and re.search(reg_exp, message.raw_text):
        return True


@client.on(NewMessage(func=filter_type))
async def forward_files(event):
    print(event.message)
    for dest in destination:
        await event.message.forward_to(dest)


@client.on(NewMessage(pattern='\/add (.+)((\n.+)+)', chats="me"))
async def add_elements(event):
    tipo = event.pattern_match.group(1)
    lista = event.pattern_match.group(2).split('\n')[1:]

    if tipo not in tables:
        await event.respond(not_exist)
        return
    if db.add_items(tipo, lista):
        await event.respond(f'Elements successfully added to {tipo}.')
        await act_list(tipo)
    else:
        await event.respond(error)


@client.on(NewMessage(pattern='\/delete (.+)\n((\s*\d)+)', chats="me"))
async def delete_elements(event):
    tipo = event.pattern_match.group(1)
    lista = event.pattern_match.group(2).split()

    if tipo not in tables:
        await event.respond(not_exist)
        return
    if db.del_items(tipo, lista):
        await event.respond(f'Items successfully deleted from  {tipo}.')
        await act_list(tipo)
    else:
        await event.respond(error)


@client.on(NewMessage(pattern='\/list (.+)', chats="me"))
async def get_elements(event):
    tipo = event.pattern_match.group(1)

    if tipo not in tables:
        await event.respond(not_exist)
        return
    lista = await act_list(tipo=tipo)

    if lista:
        final = f'**List of {tipo}**\n'
        for element in lista:
            final += f'\nid: {element.id} name: {element.att}'
        await event.respond(final)
    else:
        await event.respond(f'No items in {tipo}.')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(act_list(tipo='anime'))
    loop.create_task(act_list(tipo='channel_from'))
    loop.create_task(act_list(tipo='channel_to'))
    loop.run_forever()


