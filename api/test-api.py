# ESTE ARCHIVO ES SOLO PARA PROBAR LA CONEXIÓN A LA API DE TMDB.

import os

import requests
from dotenv import load_dotenv

load_dotenv()


def get_trending_movies():
    url = "https://api.themoviedb.org/3/trending/movie/day?language=en-US"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('API_KEY')}"
    }

    response = requests.get(url, headers=headers)
    print(response.text)


def get_popular_movies():
    url = "https://api.themoviedb.org/3/movie/popular?language=en-US&page=1"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('API_KEY')}"
    }

    response = requests.get(url, headers=headers)
    print(response.text)


if __name__ == "__main__":
    get_popular_movies()