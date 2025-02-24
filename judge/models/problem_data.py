import errno
import os
from zipfile import BadZipFile, ZipFile

from django.core.validators import FileExtensionValidator
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from judge.utils.problem_data import ProblemDataStorage


__all__ = ['problem_data_storage', 'problem_directory_file', 'ProblemData', 'ProblemTestCase', 'CHECKERS']

problem_data_storage = ProblemDataStorage()


def _problem_directory_file(code, filename):
    return os.path.join(code, os.path.basename(filename))


def problem_directory_file(data, filename):
    return _problem_directory_file(data.problem.code, filename)


CHECKERS = (
    ('standard', _('Standard')),
    ('bridged', _('Custom checker')),
    ('floats', _('Floats')),
    ('floatsabs', _('Floats (absolute)')),
    ('floatsrel', _('Floats (relative)')),
    ('rstripped', _('Non-trailing spaces')),
    ('sorted', _('Unordered')),
    ('identical', _('Byte identical')),
    ('linecount', _('Line-by-line')),
)

IO_METHODS = (
    ('standard', _('Standard Input/Output')),
    ('file', _('Via files')),
)

class ProblemData(models.Model):
    problem = models.OneToOneField('Problem', verbose_name=_('problem'), related_name='data_files',
                                   on_delete=models.CASCADE)
    zipfile = models.FileField(verbose_name=_('data zip file'), storage=problem_data_storage, null=True, blank=True,
                               upload_to=problem_directory_file)
    generator = models.FileField(verbose_name=_('generator file'), storage=problem_data_storage, null=True, blank=True,
                                 upload_to=problem_directory_file)
    output_prefix = models.IntegerField(verbose_name=_('output prefix length'), blank=True, null=True)
    output_limit = models.IntegerField(verbose_name=_('output limit length'), blank=True, null=True)
    feedback = models.TextField(verbose_name=_('init.yml generation feedback'), blank=True)
    checker = models.CharField(max_length=10, verbose_name=_('checker'), choices=CHECKERS, blank=True)
    checker_args = models.TextField(verbose_name=_('checker arguments'), blank=True,
                                    help_text=_('checker arguments as a JSON object'))
    grader_args = models.TextField(verbose_name=_('grader arguments'), blank=True,
                                    help_text=_('grader arguments as a JSON object'))
    custom_validator = models.FileField(verbose_name=_('custom checker file'),
                                        storage=problem_data_storage,
                                        null=True,
                                        blank=True,
                                        upload_to=problem_directory_file,
                                        validators=[FileExtensionValidator(allowed_extensions=['cpp', 'py'])])
    __original_zipfile = None

    def __init__(self, *args, **kwargs):
        super(ProblemData, self).__init__(*args, **kwargs)
        self.__original_zipfile = self.zipfile

    def save(self, *args, **kwargs):
        if self.zipfile != self.__original_zipfile:
            self.__original_zipfile.delete(save=False)
        return super(ProblemData, self).save(*args, **kwargs)

    def has_yml(self):
        return problem_data_storage.exists('%s/init.yml' % self.problem.code)

    def _update_code(self, original, new):
        try:
            problem_data_storage.rename(original, new)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        if self.zipfile:
            self.zipfile.name = _problem_directory_file(new, self.zipfile.name)
        if self.generator:
            self.generator.name = _problem_directory_file(new, self.generator.name)
        if self.custom_validator:
            self.custom_validator.name = _problem_directory_file(new, self.custom_validator.name)
        self.save()
    _update_code.alters_data = True


class ProblemTestCase(models.Model):
    dataset = models.ForeignKey('Problem', verbose_name=_('problem data set'), related_name='cases',
                                on_delete=models.CASCADE)
    order = models.IntegerField(verbose_name=_('case position'))
    type = models.CharField(max_length=1, verbose_name=_('case type'),
                            choices=(('C', _('Normal case')),
                                     ('S', _('Batch start')),
                                     ('E', _('Batch end'))),
                            default='C')
    input_file = models.CharField(max_length=100, verbose_name=_('input file name'), blank=True)
    output_file = models.CharField(max_length=100, verbose_name=_('output file name'), blank=True)
    generator_args = models.TextField(verbose_name=_('generator arguments'), blank=True)
    points = models.IntegerField(verbose_name=_('point value'), blank=True, null=True)
    is_pretest = models.BooleanField(verbose_name=_('case is pretest?'))
    output_prefix = models.IntegerField(verbose_name=_('output prefix length'), blank=True, null=True)
    output_limit = models.IntegerField(verbose_name=_('output limit length'), blank=True, null=True)
    checker = models.CharField(max_length=10, verbose_name=_('checker'), choices=CHECKERS, blank=True)
    checker_args = models.TextField(verbose_name=_('checker arguments'), blank=True,
                                    help_text=_('checker arguments as a JSON object'))


class PublicSolution(models.Model):
    author = models.ForeignKey("judge.Profile", verbose_name=_("user"), on_delete=models.CASCADE)
    problem = models.ForeignKey("judge.Problem", verbose_name=_("problem"), on_delete=models.CASCADE)
    contest = models.ForeignKey("judge.Contest", verbose_name=_("contest"), on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(_("solution"))
    score = models.IntegerField(_('votes'), default=0)
    created = models.DateTimeField(_("date created"), auto_now_add=True)
    approved = models.BooleanField(_("is approved"), default=False)
    point = models.IntegerField(_("point"), default=0)

    def __str__(self) -> str:
        return "Solution %s of %s" % (self.author.name, self.problem.name)

    def is_accessible_by(self, user: User):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user == self.author.user:
            return True
        return self.approved

    class Meta:
        ordering = ('-created',)


class SolutionVote(models.Model):
    voter = models.ForeignKey("judge.Profile", related_name='voted_solutions', on_delete=models.CASCADE)
    solution = models.ForeignKey(PublicSolution, related_name='votes', on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ['voter', 'solution']
        verbose_name = _('solution vote')
        verbose_name_plural = _('solution votes')