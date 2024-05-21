from fastapi import APIRouter, HTTPException
from fastapi import Request
from fastapi import Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from datetime import datetime
from datetime import timedelta
from itertools import groupby

from db.session import async_session
from api.actions.urls import _get_urls_with_pagination
from api.actions.urls import _get_urls_with_pagination_and_like
from api.actions.urls import _get_urls_with_pagination_sort
from api.actions.urls import _get_urls_with_pagination_and_like_sort

from api.actions.queries import _get_urls_with_pagination_query
from api.actions.queries import _get_urls_with_pagination_and_like_query
from api.actions.queries import _get_urls_with_pagination_sort_query
from api.actions.queries import _get_urls_with_pagination_and_like_sort_query

from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
import io

admin_router = APIRouter()

templates = Jinja2Templates(directory="static")

date_format_2 = "%Y-%m-%d"


def pad_list_with_zeros_excel(lst, amount):
    if len(lst) < amount:
        padding = [0] * (amount - len(lst))
        lst.extend(padding)
    return lst


@admin_router.post("/generate_excel_url/")
async def generate_excel(request: Request, data_request: dict):
    wb = Workbook()
    ws = wb.active
    start_date = datetime.strptime(data_request["start_date"], date_format_2)
    end_date = datetime.strptime(data_request["end_date"], date_format_2)
    main_header = []
    for i in range(int(data_request["amount"]) + 1):
        main_header.append((start_date + timedelta(days=i)).strftime(date_format_2))
        main_header.append((start_date + timedelta(days=i)).strftime(date_format_2))
        main_header.append((start_date + timedelta(days=i)).strftime(date_format_2))
        main_header.append((start_date + timedelta(days=i)).strftime(date_format_2))
    main_header = main_header[::-1]
    main_header.insert(0, "Url")
    ws.append(main_header)
    header = ["Position", "Click", "R", "CTR"] * (int(data_request["amount"]) + 1)
    header.insert(0, "")
    ws.append(header)
    if data_request["sort_result"]:
        if data_request["search_text"] == "":
            urls = await _get_urls_with_pagination_sort(data_request["start"], data_request["length"],
                                                        start_date, end_date,
                                                        data_request["sort_desc"], async_session)
        else:
            urls = await _get_urls_with_pagination_and_like_sort(data_request["start"], data_request["length"],
                                                                 start_date, end_date,
                                                                 data_request["search_text"],
                                                                 data_request["sort_desc"],
                                                                 async_session)
    else:
        if data_request["search_text"] == "":
            urls = await _get_urls_with_pagination(data_request["start"], data_request["length"],
                                                   start_date, end_date, async_session)
        else:
            urls = await _get_urls_with_pagination_and_like(data_request["start"], data_request["length"],
                                                            start_date, end_date,
                                                            data_request["search_text"],
                                                            async_session)
    try:
        grouped_data = [(key, sorted(list(group)[:14], key=lambda x: x[0])) for key, group in
                        groupby(urls, key=lambda x: x[-1])]
    except TypeError as e:
        print(urls)
        return
    if len(grouped_data) == 0:
        return {"data": []}
    for el in grouped_data:
        res = []
        for k, stat in enumerate(el[1]):
            res.append(stat[1])
            res.append(stat[2])
            res.append(stat[3])
            res.append(stat[4])
        res = pad_list_with_zeros_excel(res, 4 * (int(data_request["amount"]) + 1))
        test = res[::-1]
        test.insert(0, el[0])
        ws.append(test)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(io.BytesIO(output.getvalue()),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment;filename='data.xlsx'"})


def pad_list_with_zeros(lst, amount):
    if len(lst) < amount:
        padding = [f"""<div style='height: 55px; width: 100px; margin: 0px; padding: 0px; background-color: #B9BDBC'>
            <span style='font-size: 18px'><span style='color:red'>NAN</span></span><br>
            <span style='font-size: 10px'>Клики</span><span style='font-size: 10px; margin-left: 20px'>CTR <span style='color:red'>NAN%</span></span><br>
            <span style='font-size: 10px'><span style='color:red'>NAN</span></span> <span style='font-size: 10px; margin-left: 30px'>R <span style='color:red'>NAN%</span></span>
            </div>"""] * (amount - len(lst))
        lst.extend(padding)
    return lst


@admin_router.get("/")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@admin_router.post("/")
async def login(request: Request, username: str = Form(), password: str = Form()):
    with open('users.txt', 'r') as file:
        for line in file:
            stored_username, stored_password = line.strip().split(':')
            if username == stored_username and password == stored_password:
                return RedirectResponse("/admin/info-urls", status_code=302)
    return HTTPException(status_code=401, detail="Incorrect username or password")


@admin_router.post("/get-urls")
async def get_urls(request: Request, length: int = Form(), start: int = Form(), start_date: datetime = Form(),
                   end_date: datetime = Form(), amount: int = Form(default=14), search_text: str = Form(default=""), \
                   sort_result: bool = Form(default=False), sort_desc: bool = Form(default=False)):
    limit = length
    offset = start + 1
    if sort_result:
        if search_text == "":
            urls = await _get_urls_with_pagination_sort(offset, limit, start_date, end_date, sort_desc, async_session)
        else:
            urls = await _get_urls_with_pagination_and_like_sort(offset, limit, start_date, end_date, search_text,
                                                                 sort_desc,
                                                                 async_session)
    else:
        if search_text == "":
            urls = await _get_urls_with_pagination(offset, limit, start_date, end_date, async_session)
        else:
            urls = await _get_urls_with_pagination_and_like(offset, limit, start_date, end_date, search_text,
                                                            async_session)
    try:
        grouped_data = [(key, sorted(list(group)[:14], key=lambda x: x[0])) for key, group in
                        groupby(urls, key=lambda x: x[-1])]
    except TypeError as e:
        print(urls)
        return
    if len(grouped_data) == 0:
        return {"data": []}
    data = []
    for el in grouped_data:
        res = [
            f"<div style='width:355px; height: 55px; overflow: auto; white-space: nowrap;'><span>{el[0]}</span></div>"]
        for k, stat in enumerate(el[1]):
            up = 0
            if k + 1 < len(el[1]):
                up = round(el[1][k + 1][1] - el[1][k][1], 2)
            if up > 0:
                color = "#9DE8BD"
                color_text = "green"
            elif up < 0:
                color = "#FDC4BD"
                color_text = "red"
            else:
                color = "#B4D7ED"
                color_text = "black"
            res.append(f"""<div style='height: 55px; width: 100px; margin: 0px; padding: 0px; background-color: {color}'>
            <span style='font-size: 18px'>{stat[1]}</span><span style="margin-left: 5px; font-size: 10px; color: {color_text}">{abs(up)}</span><br>
            <span style='font-size: 10px'>Клики</span><span style='font-size: 10px; margin-left: 20px'>CTR {stat[4]}%</span><br>
            <span style='font-size: 10px'>{stat[2]}</span> <span style='font-size: 10px; margin-left: 45px'>R {stat[3]}%</span>
            </div>""")
        res = pad_list_with_zeros(res, amount + 1)
        test = res[::-1]
        test.insert(0,
                    f"<div style='width:355px; height: 55px; overflow: auto; white-space: nowrap;'><span>{el[0]}</span></div>")
        data.append(test)
    json_data = jsonable_encoder(data)

    # return JSONResponse({"data": json_data, "recordsTotal": limit, "recordsFiltered": 50000})
    return JSONResponse({"data": json_data, "recordsTotal": limit})


@admin_router.get("/info-urls")
async def get_urls(request: Request):
    response = templates.TemplateResponse("urls-info.html", {"request": request})
    return response


@admin_router.post("/get-queries")
async def get_urls(request: Request, length: int = Form(), start: int = Form(), start_date: datetime = Form(),
                   end_date: datetime = Form(), amount: int = Form(default=14), search_text: str = Form(default=""), \
                   sort_result: bool = Form(default=False), sort_desc: bool = Form(default=False)):
    limit = length
    offset = start + 1
    if sort_result:
        if search_text == "":
            urls = await _get_urls_with_pagination_sort_query(offset, limit, start_date, end_date, sort_desc,
                                                              async_session)
        else:
            urls = await _get_urls_with_pagination_and_like_sort_query(offset, limit, start_date, end_date, search_text,
                                                                       sort_desc,
                                                                       async_session)
    else:
        if search_text == "":
            urls = await _get_urls_with_pagination_query(offset, limit, start_date, end_date, async_session)
        else:
            urls = await _get_urls_with_pagination_and_like_query(offset, limit, start_date, end_date, search_text,
                                                                  async_session)
    try:
        grouped_data = [(key, sorted(list(group)[:14], key=lambda x: x[0])) for key, group in
                        groupby(urls, key=lambda x: x[-1])]
    except TypeError as e:
        print(urls)
        return
    if len(grouped_data) == 0:
        return {"data": []}
    data = []
    for el in grouped_data:
        res = [
            f"<div style='width:355px; height: 55px; overflow: auto; white-space: nowrap;'><span>{el[0]}</span></div>"]
        for k, stat in enumerate(el[1]):
            up = 0
            if k + 1 < len(el[1]):
                up = round(el[1][k + 1][1] - el[1][k][1], 2)
            if up > 0:
                color = "#9DE8BD"
                color_text = "green"
            elif up < 0:
                color = "#FDC4BD"
                color_text = "red"
            else:
                color = "#B4D7ED"
                color_text = "black"
            res.append(f"""<div style='height: 55px; width: 100px; margin: 0px; padding: 0px; background-color: {color}'>
            <span style='font-size: 18px'>{stat[1]}</span><span style="margin-left: 5px; font-size: 10px; color: {color_text}">{abs(up)}</span><br>
            <span style='font-size: 10px'>Клики</span><span style='font-size: 10px; margin-left: 20px'>CTR {stat[4]}%</span><br>
            <span style='font-size: 10px'>{stat[2]}</span> <span style='font-size: 10px; margin-left: 45px'>R {stat[3]}%</span>
            </div>""")
        res = pad_list_with_zeros(res, amount + 1)
        test = res[::-1]
        test.insert(0,
                    f"<div style='width:355px; height: 55px; overflow: auto; white-space: nowrap;'><span>{el[0]}</span></div>")
        data.append(test)

    json_data = jsonable_encoder(data)

    # return JSONResponse({"data": json_data, "recordsTotal": limit, "recordsFiltered": 50000})
    return JSONResponse({"data": json_data[::-1], "recordsTotal": limit})


@admin_router.get("/info-queries")
async def get_urls(request: Request):
    response = templates.TemplateResponse("queries-info.html", {"request": request})
    return response
