from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Hardcoded demo users 
USERS = {
    "admin": "password123",
    "researcher1": "trial2026",
    "coordinator": "sjsu2026",
}


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse(
        request, "home.html", {"user": user}
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(
        request, "login.html", {"error": None}
    )

@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if USERS.get(username) == password:
        # Save who's logged in inside the signed session cookie
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=302)
    # Wrong credentials -> show Bootstrap alert on the same page
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password."},
    )



@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    response = templates.TemplateResponse(
        request, "dashboard.html", {"user": user}
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@router.get("/logout")
def logout(request: Request):
    request.session.clear()  
    return RedirectResponse(url="/", status_code=302)