from rich.progress import Progress
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.columns import Columns
from rich.text import Text
from rich.table import Table

from PIL import Image
import os
import pypandoc
import ffmpeg
import requests
import time
import subprocess

Image.init()
console = Console()

# ASCII logo
logo = Text()
logo.append("██████╗ ██╗   ██╗ ██████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗██████╗ ████████╗\n", style="#00FF00")
logo.append("██╔══██╗╚██╗ ██╔╝██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝██╔══██╗╚══██╔══╝\n", style="#00FF66")
logo.append("██████╔╝ ╚████╔╝ ██║     ██║   ██║██╔██╗ ██║██║   ██║█████╗  ██████╔╝   ██║   \n", style="#00FF99")
logo.append("██╔═══╝   ╚██╔╝  ██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝██╔══╝  ██╔══██╗   ██║   \n", style="#00FFCC")
logo.append("██║        ██║   ╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝ ███████╗██║  ██║   ██║   \n", style="#00FFEE")
logo.append("╚═╝        ╚═╝    ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝   ╚═╝   \n", style="#00FFFF")

console.print(logo)

def make_box(title, items, color):
    content = "\n".join(f"▶ {i}" for i in items)
    return Panel(content, title=title, border_style=color)

img_box = make_box("IMAGES", ["example:", "PNG", "JPG", "WEBP", "GIF"], "cyan")
doc_box = make_box("DOCUMENTS", ["example:", "PDF", "DOCX", "TXT", "MD"], "green")
media_box = make_box("AUDIO/VIDEO", ["example:", "MP3", "WAV", "OGG"], "magenta")
help_box = make_box("HELP", ["know what to convert", "image", "document", "video"], "orange3")

console.print(Columns([img_box, doc_box, media_box, help_box]))

API_KEY = "key api"
CONVERT_URL = "https://api.chargedapi.com/convert?format=pdf"
STATUS_URL = "https://api.chargedapi.com/status/"

console.print("\n[bold cyan]Choose conversion type:[/bold cyan]")
choice_type = int(Prompt.ask("Choice", choices=["1", "2", "3", "4"]))

# HELP MENU
if choice_type == 4:
    console.print("[cyan]Help menu: 1=image, 2=document, 3=video/audio[/cyan]")
    help_choice = int(Prompt.ask("Choice", choices=["1", "2", "3"]))

    if help_choice == 1:
        print(f"OPEN formats: {', '.join(Image.OPEN.keys())}")
        print(f"SAVE formats: {', '.join(Image.SAVE.keys())}")
        Prompt.ask("Press r to return")

    if help_choice == 2:
        inp, out = pypandoc.get_pandoc_formats()
        print(f"INPUT formats: {', '.join(inp)}")
        print(f"OUTPUT formats: {', '.join(out)}")

    if help_choice == 3:
        table = Table(title="FFmpeg formats")
        table.add_column("Mode")
        table.add_column("Ext")
        table.add_column("Desc")

        raw = os.popen("ffmpeg -formats -loglevel error").read()
        for line in raw.splitlines():
            if len(line) > 15 and line[:2].strip() in ["D", "E", "DE"]:
                table.add_row(line[:4].strip(), line[4:15].strip(), line[15:].strip())

        console.print(table)
        Prompt.ask("Press r to return")

# INPUTS
file_path = console.input("File path: ")
output_ext = console.input("Output extension: ")
output_name = console.input("Output filename: ")

output_dir = r""
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, f"{output_name}.{output_ext}")
file_size = os.path.getsize(file_path)

block = 1000

# IMAGE CONVERSION
if choice_type == 1:
    with Progress() as progress:
        task = progress.add_task("Converting image...", total=file_size)
        for i in range(0, file_size, block):
            time.sleep(0.01)
            progress.update(task, advance=min(block, file_size - i))

    img = Image.open(file_path)
    img.save(output_file)

# DOCUMENT CONVERSION
elif choice_type == 2:
    if output_ext == "pdf":
        res = requests.post(CONVERT_URL, headers={"X-API-Key": API_KEY}, files={"file": open(file_path, "rb")})
        job_id = res.json()["job_id"]

        with Progress() as progress:
            task = progress.add_task("API conversion...", total=60)

            for i in range(60):
                status = requests.get(STATUS_URL + job_id, headers={"X-API-Key": API_KEY}).json()

                if status["status"] == "completed":
                    file = requests.get(status["download_url"])
                    with open(output_file, "wb") as f:
                        f.write(file.content)
                    break

                if status["status"] == "failed":
                    break

                time.sleep(1)
                progress.update(task, advance=1)

    else:
        with Progress() as progress:
            task = progress.add_task("Converting document...", total=file_size)
            for i in range(0, file_size, block):
                time.sleep(0.01)
                progress.update(task, advance=min(block, file_size - i))

        pypandoc.convert_file(file_path, to=output_ext, outputfile=output_file)

# MEDIA CONVERSION
elif choice_type == 3:
    probe = ffmpeg.probe(file_path)
    duration = float(probe["format"]["duration"])

    is_video = any(s["codec_type"] == "video" for s in probe["streams"])
    is_audio = any(s["codec_type"] == "audio" for s in probe["streams"])

    if is_video or is_audio:
        with Progress() as progress:
            task = progress.add_task("Media conversion...", total=duration)

            cmd = (
                ffmpeg.input(file_path)
                .output(output_file)
                .global_args("-progress", "pipe:1", "-loglevel", "quiet", "-y")
                .compile()
            )

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            for line in process.stdout:
                if "out_time_ms=" in line:
                    try:
                        t = int(line.split("=")[1]) / 1_000_000
                        progress.update(task, completed=t)
                    except:
                        pass

            process.wait()
            progress.update(task, completed=duration)
