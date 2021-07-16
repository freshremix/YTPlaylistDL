import os
import time
import math
import asyncio
import logging
import requests
from PIL import Image
from youtube_dl import YoutubeDL
from youtube_dl.utils import (DownloadError, ContentTooShortError,
							  ExtractorError, GeoRestrictedError,
							  MaxDownloadsReached, PostProcessingError,
							  UnavailableVideoError, XAttrMetadataError)
from asyncio import sleep
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo

from telethon import TelegramClient
from telethon import events
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
async def upload(thumb_image_path, c_time, msg, document_attributes, single_file, curr):
	try:
		ytdl_data_name_audio = os.path.basename(single_file)
		LOGGER.info(f"Uploading : {ytdl_data_name_audio}")
		await client.send_file(
			curr.chat_id,
			single_file,
			caption=f"**File Name:** __{ytdl_data_name_audio}__\n**Thanks for Using Bot**",
			force_document=False,
			supports_streaming=True,
			allow_cache=False,
			thumb=thumb_image_path,
			reply_to=curr.message.id,
			attributes=document_attributes,
			progress_callback=lambda d, t: asyncio.get_event_loop(
				).create_task(
					progress(d, t, msg, c_time, "**💬 Uploading..**",
					f"{ytdl_data_name_audio}")))
	except Exception as e:
		await client.send_message(
			event.chat_id,
			"{} caused {}".format(caption_rts, str(e)),
		)

@client.on(events.NewMessage(pattern='^/ping'))
async def pingwithtg(event):
	await event.reply("If you see this message, You verified Pedo")

@client.on(events.NewMessage(pattern='^/playlist (audio|video) (.*)'))
async def download_video(event):

	out_folder = f"downloads/{event.sender_id}/"
	#thumb_image_path = "downloads/thumb_image.jpg"
	if not os.path.isdir(out_folder):
		LOGGER.info(f"Creating folder \"{out_folder}\"")
		os.makedirs(out_folder)

	url = event.pattern_match.group(2)
	type = event.pattern_match.group(1).lower()

	msg = await event.reply("Processing...")

	if type == "audio":
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

	elif type == "video":
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
	await msg.edit("Downladed. Now Processing with FFmpeg")
	if song:
		for single_file in filename:
			if os.path.exists(os.path.splitext(single_file)[0] + ".webp"):
				im = Image.open(os.path.splitext(single_file)[0] + ".webp").convert("RGB")
				im.save(os.path.splitext(single_file)[0] + ".jpg", "jpeg")
				thumb_image_path = os.path.splitext(single_file)[0] + ".jpg"
			if os.path.exists(single_file):
				LOGGER.info(f"Processing : {single_file}")
				caption_rts = os.path.basename(single_file)
				document_attributes = []
				if single_file.endswith((".mp4", ".mp3", ".flac", ".webm")):
					metadata = extractMetadata(createParser(single_file))
					duration = 0
					width = 0
					height = 0
					if metadata.has("duration"):
						duration = metadata.get('duration').seconds
					#if os.path.exists(thumb_image_path):
					#	metadata = extractMetadata(createParser(thumb_image_path))
					#	if metadata.has("width"):
					#		width = metadata.get("width")
					#	if metadata.has("height"):
					#		height = metadata.get("height")
					#	document_attributes = [
					#		DocumentAttributeVideo(
					#			duration=duration,
					#			w=width,
					#			h=height,
					#			round_message=False,
					#			supports_streaming=True
					#		)
					#	]
					await upload(thumb_image_path, c_time, msg, document_attributes, single_file, event)
					#	continue
					os.remove(single_file)
		shutil.rmtree(out_folder)
		LOGGER.warning(f"Cleaning : {out_folder}")
	if video:
		for single_file in filename:
			if os.path.exists(os.path.splitext(single_file)[0] + ".webp"):
				im = Image.open(os.path.splitext(single_file)[0] + ".webp").convert("RGB")
				im.save(os.path.splitext(single_file)[0] + ".jpg", "jpeg")
				thumb_image_path = os.path.splitext(single_file)[0] + ".jpg"
			if os.path.exists(single_file): 
				LOGGER.info(f"Processing : {single_file}")
				caption_rts = os.path.basename(single_file)
				force_document = False
				supports_streaming = True
				document_attributes = []
				if single_file.endswith((".mp4", ".mp3", ".flac", ".webm")):
					metadata = extractMetadata(createParser(single_file))
					duration = 0
					width = 0
					height = 0
					if metadata.has("duration"):
						duration = metadata.get('duration').seconds
					#if os.path.exists(thumb_image_path):
					#	metadata = extractMetadata(createParser(thumb_image_path))
					#	if metadata.has("width"):
					#		width = metadata.get("width")
					#	if metadata.has("height"):
					#		height = metadata.get("height")
					#	document_attributes = [
					#		DocumentAttributeVideo(
					#			duration=duration,
					#			w=width,
					#			h=height,
					#			round_message=False,
					#			supports_streaming=True
					#		)
					#	]
					await upload(thumb_image_path, c_time, msg, document_attributes, single_file, event)
					#	continue
					os.remove(single_file)
		shutil.rmtree(out_folder)
		LOGGER.warning(f"Cleaning : {out_folder}")
		
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
