from argparse import ArgumentParser
from PyInquirer import prompt
import pickle
import os
from Sakurajima.api import Sakurajima

class Kaguya(object):
    def __init__(self):
        self.user_details = None
        self.start()

    def start(self):
        parser = ArgumentParser(description="Yukinoshita is a CLI tool built with the purpose of\
         downloading anime from aniwatch.me.")

        parser.add_argument(
             "command", 
             help = "Issue a command like 'setup' or 'download'."
        )
        download_group = parser.add_argument_group('download')
        download_group.add_argument(
            "-fn", "--filename",
            help = "The name of the downloaded file."
        )
        download_group.add_argument(
            "-s", "--search",
            help = "Skips the prompt asking for search query and directly searches the given title."
        )
        download_group.add_argument(
            "-q", "--quality",
            help = "Skips the prompt for quality and automatically selects this quality."
        )
        download_group.add_argument(
            "--include-intro",
            help = "Include the 5 second aniwatch intro, This can cause playback issues on certain players.",
            action = "store_true",
            default = False
        )
        download_group.add_argument(
            "--keep-chunks",
            help = "Setting this flag will not delete video chunks after merge.",
            action = "store_true",
            default = False
        )
        download_group.add_argument(
            "-id","--id",
            help = "Skips search and gets the anime by its ID.",
            type = int
        )
        download_group.add_argument(
            "--multi-thread",
            help = "Adding this flag will use multiple threads for downloading.",
            action = "store_true",
            default = False
        )
        download_group.add_argument(
            "--max-threads",
            help = "Set the number of threads that will be used for downloading.",
            type = int,
        )
        download_group.add_argument(
            "--no-ffmpeg",
            help = "Setting this flag will use Sakurajima's ChunkMerger. Warning : This can cause playback issues.",
            action = "store_true",
            default = False
        )
        reset_group = parser.add_argument_group('reset')
        reset_group.add_argument(
            "--hard",
            help="Deletes the stored login data",
            action="store_true"
        )
        user_group = parser.add_argument_group('user')
        user_group.add_argument(
            "-a", "--all",
            help="Returns all details, including auth token",
            action="store_true"
        )

        self.args = parser.parse_args()
        if self.args.command == 'setup':
            self.setup_user()
        elif self.args.command == 'download':
            self.init_search()
        elif self.args.command == 'reset':
            self.reset_login()
        elif self.args.command == 'user':
            self.print_login_details()


    def setup_user(self):
        if self.validate_login_details():
            print("Setup already complete! Use the 'download' command to download animes!")
            print("If you want to change login details use the 'reset'")
        else:
            self.get_login_details_from_user()

    def get_login_details_from_user(self):
        login_details = {}
        login_details["username"] = input("Enter your username : ")
        login_details["userID"] = input("Enter your user ID : ")
        login_details["authToken"] = input("Enter your auth token : ")
        with open(".login", "wb") as filehandle:
            pickle.dump(login_details, filehandle)
        print("Setup complete, use the download command to search and download anime")

    def print_login_details(self):
        login_details = self.read_login_details_from_file()
        if self.args.all:
            print("Username: ", login_details["username"])
            print("User ID: ", login_details["userID"])
            print("Auth Token: ", login_details["authToken"])
        else:
            print("Username: ", login_details["username"])

    def read_login_details_from_file(self):
        if self.user_details is None:
            self.validate_login_details()
            with open(".login", "rb") as filehandle:
                login_details = pickle.load(filehandle)
            return login_details
        else:
            return self.user_details
    
    def init_search(self):
        if self.validate_login_details():
            login_details = self.read_login_details_from_file()
            self.client = Sakurajima(
                login_details['username'],
                login_details['userID'],
                login_details['authToken']
            )
            if self.args.id:
                self.get_anime_by_id()
            else:
                self.search_anime()
        else:
            print("No login details found.")
            print("Use the 'setup' command to setup a user.")
    
    def validate_login_details(self):
        if os.path.isfile(".login") == True:
            return True
        else:
            return False

    def reset_login(self):
        if self.args.hard:
            if self.validate_login_details():
                os.remove(".login")
                print("Login details removed.")
            else:
                print("No login details found.")
        else:
            self.get_login_details_from_user()

    def search_anime(self):
        if self.args.search:
            search_query = self.args.search
        else:
            search_query = input("Enter the name of the anime you want to search : ")
        search_results = self.client.search(search_query)
        self.choose_anime(search_results)

    def get_anime_by_id(self):
        anime = self.client.get_anime(self.args.id)
        self.choose_episode(anime)
    
    def choose_anime(self, search_results):
        dummy_animes = [{'title':'hxh', 'ep' : 148},{"title": "kaguya", "ep":12}]
        
        choices = {
            "type" : "list",
            "name" : 'anime',
            "message" : "Choose the anime you want to download",
            "choices" : [{"name": anime.title, "value": anime} for anime in search_results]
        }
        choosen_anime = prompt(choices)['anime']
        self.choose_episode(choosen_anime)

    def choose_episode(self, choosen_anime):
        episodes = choosen_anime.get_episodes()
        print(f"{len(episodes)} episode(s) found")
        episode_choice = int(input("Enter the episode number you want to download: "))
        choosen_episode = episodes.get_episode_by_number(episode_choice)
        if self.args.quality:
            choosen_quality = self.args.search
        else:
            mapped_quality_choices = self.map_qualites_choices(
                choosen_episode.get_available_qualities()
            )
            quality_choices = {
                "type" : "list",
                "name" : "quality",
                "message" : "Choose the quality you want to download",
                "choices" : [
                    {"name": mapped_quality["quality"], "value": mapped_quality["value"]} 
                    for mapped_quality in mapped_quality_choices
                    ] 
            }
            choosen_quality = prompt(quality_choices)['quality']

        self.download_episodes(choosen_episode, choosen_quality)
        print(f"would have downloaded {choosen_quality}")
    def download_episodes(self, choosen_episode, choosen_quality):
        choosen_episode.download(
            quality = choosen_quality,
            file_name = self.args.fn,
            multithreading = self.args.multi_thread,
            max_threads = self.args.max_threads if self.args.max_threads else 4,
            use_ffmpeg = not self.args.no_ffmpeg,
            include_intro = self.args.include_intro,
            delete_chunks = not self.args.keep_chunks,
        )
        
    def map_qualites_choices(self, qualities_list):
        QUALITY_MAP = {
            "ld" : "360p",
            "sd" : "480p",
            "hd" : "720p",
            "fullhd" : "1080p"
            }
        return [
            {"quality" : QUALITY_MAP[quality],
            "value" : quality}
            for quality in qualities_list
            ]

if __name__ =="__main__":
    Kaguya()