# coding=utf-8
from audioop import reverse
import re

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import get_default_password_validators
from django.forms import ChoiceField, ModelChoiceField, ModelMultipleChoiceField
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext, gettext_lazy as _
from registration.backends.default.views import (ActivationView as OldActivationView,
                                                 RegistrationView as OldRegistrationView)
from registration.forms import RegistrationForm
# from sortedm2m.forms import SortedMultipleChoiceField

from judge.models import Language, Organization, Profile, TIMEZONE
from judge.utils.recaptcha import ReCaptchaField, ReCaptchaWidget
from judge.utils.subscription import Subscription, newsletter_id
from judge.widgets import Select2MultipleWidget, Select2Widget

bad_mail_regex = list(map(re.compile, settings.BAD_MAIL_PROVIDER_REGEX))


class CustomRegistrationForm(RegistrationForm):
    username = forms.RegexField(regex=r'^(?=.{6,30}$)(?![_.])(?!.*[_.]{2})[a-z0-9_]+(?<![_.])$', max_length=30, label=_('Username'),
                                error_messages={'invalid': _('A username must contain lower latinh letters, '
                                                             'numbers, min length = 6, max length = 30')})
    timezone = ChoiceField(label=_('Timezone'), choices=TIMEZONE,
                           widget=Select2Widget(attrs={'style': 'width:100%'}))
    language = ModelChoiceField(queryset=Language.objects.all(), label=_('Preferred language'), empty_label=None,
                                widget=Select2Widget(attrs={'style': 'width:100%'}))
    organizations = ModelMultipleChoiceField(queryset=Organization.objects.filter(is_open=True),
                                              label=_('Organizations'), required=False,
                                              widget=Select2MultipleWidget(attrs={'style': 'width:100%'}))
    name = forms.RegexField(regex=r'^(?!\s*$).+', max_length=50, required=True, label=_('Fullname'))

    if newsletter_id is not None:
        newsletter = forms.BooleanField(label=_('Subscribe to newsletter?'), initial=True, required=False)

    if ReCaptchaField is not None:
        captcha = ReCaptchaField(widget=ReCaptchaWidget())

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            raise forms.ValidationError(gettext('The email address "%s" is already taken. Only one registration '
                                                'is allowed per address.') % self.cleaned_data['email'])
        if '@' in self.cleaned_data['email']:
            domain = self.cleaned_data['email'].split('@')[-1].lower()
            if (domain in settings.BAD_MAIL_PROVIDERS or
                    any(regex.match(domain) for regex in bad_mail_regex)):
                raise forms.ValidationError(gettext('Your email provider is not allowed due to history of abuse. '
                                                    'Please use a reputable email provider.'))
        return self.cleaned_data['email']


class RegistrationView(OldRegistrationView):
    title = _('Registration')
    form_class = CustomRegistrationForm
    template_name = 'registration/registration_form.html'

    def get_success_url(self, user=None):
        return reverse_lazy('auth_login')

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        tzmap = settings.TIMEZONE_MAP
        kwargs['TIMEZONE_MAP'] = tzmap or 'http://momentjs.com/static/img/world.png'
        kwargs['TIMEZONE_BG'] = settings.TIMEZONE_BG if tzmap else '#4E7CAD'
        kwargs['password_validators'] = get_default_password_validators()
        kwargs['tos_url'] = settings.TERMS_OF_SERVICE_URL
        return super(RegistrationView, self).get_context_data(**kwargs)

    def register(self, form):
        user = super(RegistrationView, self).register(form)
        user.is_active = True
        user.save()
        profile, _ = Profile.objects.get_or_create(user=user, defaults={
            'language': Language.get_default_language(),
        })

        cleaned_data = form.cleaned_data
        profile.timezone = cleaned_data['timezone']
        profile.name = cleaned_data['name']
        profile.language = cleaned_data['language']
        profile.organizations.add(*cleaned_data['organizations'])
        profile.save()

        if newsletter_id is not None and cleaned_data['newsletter']:
            Subscription(user=user, newsletter_id=newsletter_id, subscribed=True).save()
        return user

    def get_initial(self, *args, **kwargs):
        initial = super(RegistrationView, self).get_initial(*args, **kwargs)
        initial['timezone'] = settings.DEFAULT_USER_TIME_ZONE
        initial['language'] = Language.objects.get(key=settings.DEFAULT_USER_LANGUAGE)
        return initial


class ActivationView(OldActivationView):
    title = _('Registration')
    template_name = 'registration/activate.html'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(ActivationView, self).get_context_data(**kwargs)


def social_auth_error(request):
    return render(request, 'generic-message.html', {
        'title': gettext('Authentication failure'),
        'message': request.GET.get('message'),
    })
