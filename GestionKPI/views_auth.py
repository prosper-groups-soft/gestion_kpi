from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from SMQ.models import UserProfile
from django.contrib.auth import get_user_model


User = get_user_model()


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email ou mot de passe incorrect.")
            return render(request, "auth.html")

        user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            login(request, user)
            try:
                departement = user.userprofile.departement
            except UserProfile.DoesNotExist:
                messages.error(request, "Profil utilisateur introuvable.")
                return render(request, "auth.html")


            print(departement)

            redirect_map = {
                "SMQ": "/smq/tableau-bord/",
                "Ressources humaines": "/departement/ressources-humaines/tableau-bord/",
                "Ventes": "/departement/ventes/tableau-bord/",
                "Garage": "/departement/garage/tableau-bord/",
            }

            return redirect(redirect_map.get(departement, "login"))
        else:
            messages.error(request, "Email ou mot de passe incorrect.")

    return render(request, "auth.html")


def logout_view(request):
    logout(request)

    storage = messages.get_messages(request)
    for _ in storage:
        pass

    return redirect("auth")


