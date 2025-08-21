from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages
from .models import UserProfile


def utilisateurs(request):
    # Recherche
    search_query = request.GET.get('q', '')
    departement_filter = request.GET.get('departement', '')
    page_number = request.GET.get('page', 1)

    user_profiles = UserProfile.objects.select_related('user')

    if search_query:
        user_profiles = user_profiles.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__identifiant__icontains=search_query)
        )
    if departement_filter:
        user_profiles = user_profiles.filter(departement=departement_filter)

    paginator = Paginator(user_profiles.order_by('user__last_name'), 10)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'departement_filter': departement_filter,
        'pagename': "utilisateurs",
    }
    return render(request, "smq/utilisateurs.html", context)


def add_utilisateurs(request):
    if request.method == "POST":
        data = request.POST
        full_name = data['full_name'].strip()
        first_name = full_name.split(' ')[0]
        last_name = ' '.join(full_name.split(' ')[1:]) if len(full_name.split(' ')) > 1 else ''
        try:
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password'],
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.create(
                user=user,
                sexe=data['sexe'],
                date_naissance=data['date_naissance'],
                numero_telephone=data['numero_telephone'],
                departement=data['departement'],
                plain_password=data['password'],
                identifiant=data['identifiant'],
            )
            messages.success(request, "Utilisateur ajouté avec succès.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout : {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', reverse('smq/utilisateurs')))
    return redirect('smq/utilisateurs')


def edit_utilisateurs(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        user_profile = get_object_or_404(UserProfile, pk=user_id)

        data = request.POST
        user = user_profile.user
        full_name = data['full_name'].strip()
        if ' ' in full_name:
            user.first_name, user.last_name = full_name.split(' ', 1)
        else:
            user.first_name = full_name
            user.last_name = ''

        user.email = data['email']
        if data['password']:
            user.set_password(data['password'])
            user_profile.plain_password = data['password']
        user.save()

        user_profile.sexe = data['sexe']
        user_profile.date_naissance = data['date_naissance']
        user_profile.numero_telephone = data['numero_telephone']
        user_profile.departement = data['departement']
        user_profile.identifiant = data['identifiant']
        user_profile.save()

        messages.success(request, "Utilisateur modifié avec succès.")
        return redirect(request.META.get('HTTP_REFERER', reverse('smq/utilisateurs')))

    return redirect('smq/utilisateurs')


def delete_utilisateurs(request, user_id):
    user_profile = get_object_or_404(UserProfile, pk=user_id)
    user_profile.user.delete()
    user_profile.delete()
    messages.success(request, "Utilisateur supprimé avec succès.")
    return redirect(request.META.get('HTTP_REFERER', reverse('smq/utilisateurs')))

