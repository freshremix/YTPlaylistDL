import os
import time
import math
import asyncio
import logging
from pathlib import Path
from youtube_dl import YoutubeDL
from youtube_dl.utils import (DownloadError, ContentTooShortError,
							  ExtractorError, GeoRestrictedError,
							  MaxDownloadsReached, PostProcessingError,
							  UnavailableVideoError, XAttrMetadataError)
from asyncio import sleep
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo
tdb = {}
from telethon import TelegramClient
from telethon import events, Button
from telethon.sessions import StringSession

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from telethon.tl.types import DocumentAttributeAudio
import shutil

logging.basicConfig(
	level=logging.INFO,
	format='%(name)s - [%(levelname)s] - %(message)s'
)
LOGGER = logging.getLogger(__name__)

# --- CREATE TELEGRAM CLIENT --- #
client = TelegramClient('bot', int(os.environ.get("APP_ID")), os.environ.get("API_HASH")).start(bot_token=os.environ.get("TOKEN"))

# --- PROGRESS DEF --- #
async def progress(current, total, event, start, type_of_ps, file_name=None):
	now = time.time()
	diff = now - start
	if round(diff % 10.00) == 0 or current == total:
		percentage = current * 100 / total
		speed = current / diff
		elapsed_time = round(diff) * 1000
		time_to_completion = round((total - current) / speed) * 1000
		estimated_total_time = elapsed_time + time_to_completion
		progress_str = "{0}{1} {2}%\n".format(
			''.join(["█" for i in range(math.floor(percentage / 10))]),
			''.join(["░" for i in range(10 - math.floor(percentage / 10))]),
			round(percentage, 2))
		tmp = progress_str + \
			"{0} of {1}\n**Speed:** {2}/s\n**ETA:** {3}".format(
				humanbytes(current),
				humanbytes(total),
				humanbytes(speed),
				time_formatter(estimated_total_time)
			)
		if file_name:
			await event.edit("{}\n**File Name:** {}\n{}".format(
				type_of_ps, file_name, tmp))
		else:
			await event.edit("{}\n{}".format(type_of_ps, tmp))

# --- HUMANBYTES DEF --- #
def humanbytes(size):
	if not size:
		return ""
	# 2 ** 10 = 1024
	power = 2**10
	raised_to_pow = 0
	dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
	while size > power:
		size /= power
		raised_to_pow += 1
	return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

# --- TIME FORMATTER DEF --- #
def time_formatter(milliseconds: int) -> str:
	seconds, milliseconds = divmod(int(milliseconds), 1000)
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	tmp = ((str(days) + " day(s), ") if days else "") + \
		((str(hours) + " hour(s), ") if hours else "") + \
		((str(minutes) + " minute(s), ") if minutes else "") + \
		((str(seconds) + " second(s), ") if seconds else "") + \
		((str(milliseconds) + " millisecond(s), ") if milliseconds else "")
	return tmp[:-2]

# --- FILE UPLOAD DEF --- #
async def upload(thumb_image_path, c_time, msg, single_file, curr):
	try:
		file_name = os.path.basename(single_file)
		LOGGER.info(f"Uploading : {file_name}")
		await client.send_file(
			curr.chat_id,
			single_file,
			caption=f"**File Name:** {file_name}__\n**Thanks for Using Bot**",
			force_document=False,
			supports_streaming=True,
			allow_cache=False,
			thumb=thumb_image_path,
			progress_callback=lambda d, t: asyncio.get_event_loop(
				).create_task(
					progress(d, t, msg, c_time, "**💬 Uploading..**",
					f"{file_name}")))
	except Exception as e:
		await msg.edit(
			"{} caused {}".format(caption_rts, str(e)),
		)

@client.on(events.NewMessage(pattern='^/ping'))
async def pingwithtg(event):
	await event.reply("If you see this message, You verified Pedo")

@client.on(events.CallbackQuery(pattern='vid(_/(.*))'))
async def ptype_vid(e):
	event_id = int(((e.pattern_match.group(1).decode())).split("_", 1)[1])
	ptype = "video"
	url = tdb[event_id]
	await download_process(url, ptype, event_id, e.chat_id)

@client.on(events.CallbackQuery(pattern='aud(_/(.*))'))
async def ptype_aud(event):
	event_id = int(((e.pattern_match.group(1).decode())).split("_", 1)[1])
	ptype = "audio"
	url = tdb[event_id]
	await download_process(url, ptype, event_id, e.chat_id)


@client.on(events.NewMessage(pattern='^/playlist (.*)'))
async def processing(event):

	out_folder = f"downloads/{event.sender_id}/"
	if not os.path.isdir(out_folder):
		LOGGER.info(f"Creating folder \"{out_folder}\"")
		os.makedirs(out_folder)
	url = event.pattern_match.group(1)
	tdb[event.id] = url
	msg = await event.reply("💬 Choose file type before download.", buttons=[
			Button.inline('📹 Video', data='vid'),
			Button.inline('🎵 Audio', data='aud')
		])

	# Bitch Stopppp!!! Wait till callback response 

async def download_process(url, pytype, reply_id, chat_id):
	if ptype == "audio":
		opts = {
			'format':'bestaudio',
			'addmetadata':True,
			'noplaylist': False,
			'key':'FFmpegMetadata',
			'writethumbnail':True,
			'embedthumbnail':True,
			'prefer_ffmpeg':True,
			'geo_bypass':True,
			'nocheckcertificate':True,
			'postprocessors': [{
				'key': 'FFmpegExtractAudio',
				'preferredcodec': 'mp3',
				'preferredquality': '320',
			}],
			'outtmpl':out_folder + '%(title)s.%(ext)s',
			'quiet':True,
			'logtostderr':False
		}
		video = False
		song = True

	elif ptype == "video":
		opts = {
			'format':'best',
			'addmetadata':True,
			'noplaylist': False,
			'getthumbnail':True,
			'embedthumbnail': True,
			'xattrs':True,
			'writethumbnail': True,
			'key':'FFmpegMetadata',
			'prefer_ffmpeg':True,
			'geo_bypass':True,
			'nocheckcertificate':True,
			'postprocessors': [{
				'key': 'FFmpegVideoConvertor',
				'preferedformat': 'mp4'},],
			'outtmpl':out_folder + '%(title)s.%(ext)s',
			'logtostderr':False,
			'quiet':True
		}
		song = False
		video = True
	msg = await client.send_message(chat_id, "Downloading Started..", reply_to=reply_to)
	try:
		await msg.edit("**Downloading Playlist.**\nDo not add new tasks. Else **ban** from bot!")
		with YoutubeDL(opts) as ytdl:
			ytdl_data = ytdl.extract_info(url)
		filename = sorted(get_lst_of_files(out_folder, []))
	except DownloadError as DE:
		await msg.edit(f"{str(DE)}")
		return
	except ContentTooShortError:
		await msg.edit("The download content was too short.")
		return
	except GeoRestrictedError:
		await msg.edit(
			"Video is not available from your geographic location due to geographic restrictions imposed by a website."
		)
		return
	except MaxDownloadsReached:
		await msg.edit("Max-downloads limit has been reached.")
		return
	except PostProcessingError:
		await msg.edit("There was an error during post processing.")
		return
	except UnavailableVideoError:
		await msg.edit("Media is not available in the requested format.")
		return
	except XAttrMetadataError as XAME:
		await msg.edit(f"{XAME.code}: {XAME.msg}\n{XAME.reason}")
		return
	except ExtractorError:
		await msg.edit("There was an error during info extraction.")
		return
	except Exception as e:
		await msg.edit(f"{str(type(e)): {str(e)}}")
		return
	c_time = time.time()
	await msg.edit("Downladed Success! ✅")

	if song:

		for single_file in filename:

			thumb_image_path = Path(f"{single_file}.jpg")
			if not os.path.exists(thumb_image_path):
				thumb_image_path = Path(f"{single_file}.webp")
			elif not os.path.exists(thumb_image_path):
				thumb_image_path = None

			await upload(thumb_image_path, c_time, msg, single_file, event)

			os.remove(single_file)

		shutil.rmtree(out_folder)
		LOGGER.warning(f"Cleaning : {out_folder}")

		await msg.delete()
		await client.send_message(chat_id, "Playlist Uploaded Success! ✅")

	if video:

		for single_file in filename:

			thumb_image_path = Path(f"{single_file}.jpg")
			if not os.path.exists(thumb_image_path):
				thumb_image_path = Path(f"{single_file}.webp")
			elif not os.path.exists(thumb_image_path):
				thumb_image_path = None

			await upload(thumb_image_path, c_time, msg, single_file, event)

			os.remove(single_file)

		shutil.rmtree(out_folder)
		LOGGER.warning(f"Cleaning : {out_folder}")

		await msg.delete()
		await client.send_message(chat_id, "Playlist Uploaded Success! ✅")

def get_lst_of_files(input_directory, output_lst):
	filesinfolder = os.listdir(input_directory)
	for file_name in filesinfolder:
		current_file_name = os.path.join(input_directory, file_name)
		if os.path.isdir(current_file_name):
			return get_lst_of_files(current_file_name, output_lst)
		output_lst.append(current_file_name)
	return output_lst
 
print("> Bot Started ")
client.run_until_disconnected()
