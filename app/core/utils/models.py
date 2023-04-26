from django.db import models


class TimestampModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ExtraModel:
    class Meta:
        admin_list_display = "__all__"

    @classmethod
    def get_list_display(self):
        list_display = self.Meta.admin_list_display
        if isinstance(list_display, str):
            _dict = self.__dict__
            del _dict["objects"]
            return _dict.keys()

        return list_display


class AppModel(TimestampModel, ExtraModel):
    class Meta:
        abstract = True
