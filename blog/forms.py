"""
bbs用到的form类
"""

from django import forms
from django.core.exceptions import ValidationError


# 定义一个form类
class RegForm(forms.Form):
    username = forms.CharField(
        max_length=16,
        label="用户名",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        error_messages={
            "max_length": "用户名最长十六位!",
            "required": "用户名不能为空!"
        }
    )

    password = forms.CharField(
        min_length=6,
        label="密码",
        widget=forms.PasswordInput(attrs={"class": "form-control"},
                                   # render_value=True
                                   ),
        error_messages={
            "min_length": "密码最少要6位!",
            "required": "密码不能为空!"
        },

    )

    re_password = forms.CharField(
        min_length=6,
        label="确认密码",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        error_messages={
            "min_length": "确认密码最少要6位!",
            "required": "确认密码不能为空!"
        }
    )

    email = forms.EmailField(
        label="邮箱",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        error_messages={
            "invalid": "邮箱格式不正确!",
            "required": "邮箱不能为空!"
        }
    )

    # 重写全局的钩子函数，对确认密码做校验
    def clean(self):
        password = self.cleaned_data.get("password")
        re_password = self.cleaned_data.get("re_password")

        if re_password and re_password != password:
            self.add_error("re_password", ValidationError("两次密码不一致"))

        else:
            return self.cleaned_data

