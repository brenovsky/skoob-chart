import requests
import json
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import io
from io import BytesIO
import time
from datetime import datetime

# Colocar todos os livros lidos em uma única página
def mock_first_page(url, headers, user_id, year):
    try:
        response = requests.get(url, headers=headers)
        response_json = response.json()
        total_books = response_json["paging"]["total"]

        new_url = f"https://www.skoob.com.br/v1/bookcase/books/{user_id}/year:{year}/page:1/limit:{total_books}/"

        return new_url
    except Exception(e):
        print(e)

def improve_image_quality(book_img):

    # Aumentar a nitidez
    enhancer = ImageEnhance.Sharpness(book_img)
    book_img = enhancer.enhance(1.5)

    # Aumentar o contraste
    enhancer = ImageEnhance.Contrast(book_img)
    book_img = enhancer.enhance(1)

    # Aumentar a saturação
    enhancer = ImageEnhance.Color(book_img)
    book_img = enhancer.enhance(1)

    # Aplicar um filtro de nitidez adicional (opcional)
    book_img = book_img.filter(ImageFilter.SHARPEN)

    return book_img

def openStar(star_type):
    # Estrela cheia
    if star_type == 0:
        img_star = Image.open("static/images/star-3.png").convert("RGBA")
        return img_star.resize((44, 44))
    
    # Meia estrela
    img_star = Image.open("static/images/half-star-3.png").convert("RGBA")
    return img_star.resize((44, 44))

def pasteStar(book_json, book_img):
    book_rating = book_json["ranking"]

    if book_rating == 0:
        return book_img

    if book_rating == 0.5:
        img_half_star = openStar(1)
        book_img.paste(img_half_star, (8, 575), img_half_star)

        return book_img

    for i in range(int(book_rating)):
        img_star = openStar(0)
        book_img.paste(img_star, (8 + (i * 50), 575), img_star)
    
    if type(book_rating) == float:
        img_half_star = openStar(1)
        book_img.paste(img_half_star, (8 + ((i + 1) * 50), 575), img_half_star)
    
    return book_img

def apply_gradient(book_img):
    width = book_img.width
    height = book_img.height

    book_img = book_img.convert("RGBA")

    gradient = Image.new("L", (width, height), color=0)  # Modo 'L' é para 8-bit (escala de cinza)
    draw = ImageDraw.Draw(gradient)

    gradient_height = int(height * 0.25)

    for y in range(gradient_height):
        opacity = int(180 * (y / gradient_height))
        draw.line([(0, height - gradient_height + y), (width, height - gradient_height + y)], fill=opacity)

        gradient_alpha = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
        gradient_alpha.putalpha(gradient)

    return Image.alpha_composite(book_img, gradient_alpha)

def create_byte_image_array(response_json, book_quantity, year, user_id):
    chart_imgs = {}
    total_books_json = response_json["paging"]["total"]

    book_count = 0

    while book_count < book_quantity:

        if total_books_json <= book_count:
            year -= 1
            previous_year_url = f"https://www.skoob.com.br/v1/bookcase/books/{user_id}/year:{year}/page:1/limit:1/"

            previous_year_url = mock_first_page(previous_year_url, headers, user_id, year)

            response = requests.get(previous_year_url, headers=headers)

            response_json = response.json()

            total_books_json = response_json["paging"]["total"]


        # Algoritmo para varrer JSON
        for i in range(total_books_json - 1, -1, -1):

            target_element = response_json["response"][i]

            book_edition = target_element["edicao"]
            book_name = book_edition["titulo"]
            book_img = book_edition["capa_grande"]

            response_img = requests.get(book_img, headers=headers)

            # BytesIO converte para que Image consiga ler a requisição
            book_img_byte = Image.open(BytesIO(response_img.content))

            # Melhorar qualidade
            # book_img_byte = improve_image_quality(book_img_byte)

            new_size = (419, 633)
            book_img_resized = book_img_byte.resize(new_size, Image.Resampling.LANCZOS)


            book_img_resized = apply_gradient(book_img_resized)
            book_img_resized = pasteStar(target_element, book_img_resized)

            book_img_resized = book_img_resized.convert("RGB")

                # Salva dinamicamente a imagem em bytes em um array
            img_byte_value = io.BytesIO()

            book_img_resized.save(img_byte_value, format="JPEG")
            chart_imgs[f"{book_count}-{book_name}"] = img_byte_value.getvalue()

            book_count += 1

            if book_count == book_quantity:
                break
    
    return chart_imgs
# Gerar grid de imagens
def create_grid(columns, lines, chart_imgs):
    new_size = (419, 633)

    chart_width = new_size[0] * columns
    chart_height = new_size[1] * lines

    book_count = 0

    grid = Image.new("RGB", (chart_width, chart_height), (255, 255, 255))

    for book, image_bytes in chart_imgs.items():

        if book_count >= book_quantity:
            break
            
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")

        x = (book_count % columns) * new_size[0]
        y = (book_count // columns) * new_size[1]

        grid.paste(image, (x, y))

        book_count += 1

    grid.save(f"grid{columns}x{lines}.jpg")

user_id = input("input your profile id: ")

year = 2024

url = f"https://www.skoob.com.br/v1/bookcase/books/{user_id}/year:{year}/page:1/limit:1/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

new_url = mock_first_page(url, headers, user_id, year)

response = requests.get(new_url, headers=headers)

print(response.status_code)

if response.status_code == 200:
    response_json = response.json()
    # with open("log.json", "w", encoding="utf-8") as file:
    #      json.dump(response_json, file, indent=4, ensure_ascii=False)
    
    columns, lines = map(int, input("Selecione o tamanho do grid:").split())
    book_quantity = columns * lines

    try:
        inicio = time.time()

        chart_imgs = create_byte_image_array(response_json, book_quantity, year, user_id)

        create_grid(columns, lines, chart_imgs)

        fim = time.time()
        
        print(fim - inicio)
    except Exception as e:
        print(e)