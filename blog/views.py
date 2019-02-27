import os, json
from bbs import settings
from bs4 import BeautifulSoup
from django.shortcuts import render, HttpResponse, redirect
from django.http import JsonResponse
from django.contrib import auth
from geetest import GeetestLib
from blog import forms, models
from django.db.models import Count, F

# Create your views here.


# 使用极验滑动验证码的登录
def login(request):
    # if request.is_ajax():  # 如果是AJAX请求
    if request.method == "POST":
        # 初始化一个给AJAX返回的数据
        ret = {"status": 0, "msg": ""}
        # 从提交过来的数据中 取到用户名和密码
        username = request.POST.get("username")
        pwd = request.POST.get("password")
        # 获取极验 滑动验证码相关的参数
        gt = GeetestLib(pc_geetest_id, pc_geetest_key)
        challenge = request.POST.get(gt.FN_CHALLENGE, '')
        validate = request.POST.get(gt.FN_VALIDATE, '')
        seccode = request.POST.get(gt.FN_SECCODE, '')
        status = request.session[gt.GT_STATUS_SESSION_KEY]
        user_id = request.session["user_id"]

        if status:
            result = gt.success_validate(challenge, validate, seccode, user_id)
        else:
            result = gt.failback_validate(challenge, validate, seccode)

        if result:
            # 验证码正确
            # 利用auth模块做用户名和密码的校验
            user = auth.authenticate(username=username, password=pwd)
            if user:
                # 用户名密码正确
                # 给用户做登录
                auth.login(request, user)  # 将登录用户赋值给 request.user
                ret["msg"] = "/index/"
            else:
                # 用户名密码错误
                ret["status"] = 1
                ret["msg"] = "用户名或密码错误！"
        else:
            ret["status"] = 1
            ret["msg"] = "验证码错误"

        return JsonResponse(ret)
    return render(request, "login.html")


# 请在官网申请ID使用，示例ID不可使用
pc_geetest_id = "b46d1900d0a894591916ea94ea91bd2c"
pc_geetest_key = "36fc3fe98530eea08dfc6ce76e3d24c4"


def get_geetest(request):
    user_id = 'test'
    gt = GeetestLib(pc_geetest_id, pc_geetest_key)
    status = gt.pre_process(user_id)
    request.session[gt.GT_STATUS_SESSION_KEY] = status
    request.session["user_id"] = user_id
    response_str = gt.get_response_str()
    return HttpResponse(response_str)


def logout(request):
    auth.logout(request=request)
    return redirect("/login/")


def index(request):
    article_list = models.Article.objects.all()
    return render(request, 'index.html', context={"article_list": article_list})


def register(request):
    if request.method == 'POST':
        ret = {"status": 0, "msg": ""}
        form_obj = forms.RegForm(request.POST)

        if form_obj.is_valid():
            form_obj.cleaned_data.pop("re_password")
            avatar = request.FILES.get("avatar")
            models.UserInfo.objects.create_user(**form_obj.cleaned_data, avatar=avatar)
            ret["msg"] = "/index/"
            return JsonResponse(ret)

        else:
            ret["status"] = 1
            ret["msg"] = form_obj.errors
            return JsonResponse(ret)

    else:
        form_obj = forms.RegForm()
        return render(request, 'register.html', {'form_obj': form_obj})


def check_username_exist(requst):
    ret = {"status":0, "msg":""}
    username = requst.GET.get("username")
    is_exist = models.UserInfo.objects.filter(username=username)
    if is_exist:
        ret["status"] = 1
        ret["msg"] = "用户名已存在!"
    return JsonResponse(ret)


def get_left_menu(username):
    user = models.UserInfo.objects.filter(username=username).first()
    blog = user.blog
    category_list = models.Category.objects.filter(blog=blog).annotate(c=Count("article")).values("title", "c")
    tag_list = models.Tag.objects.filter(blog=blog).annotate(c=Count("article")).values("title", "c")
    # 按日期归档
    archive_list = models.Article.objects.filter(user=user).extra(
        select={"archive_ym": "date_format(create_time,'%%Y-%%m')"}
    ).values("archive_ym").annotate(c=Count("nid")).values("archive_ym", "c")
    return category_list, tag_list, archive_list


def home(request, username):
    user = models.UserInfo.objects.filter(username=username).first()
    if not user:
        return HttpResponse("404")
    else:
        blog = user.blog
        article_list = models.Article.objects.filter(user=user)
        return render(request, "home.html", {
            "username": username,
            "blog": blog,
            "article_list": article_list,
        })


def article_detail(request, username, pk):
    user = models.UserInfo.objects.filter(username=username).first()
    if not user:
        return HttpResponse("404")
    blog = user.blog
    # 找到当前的文章
    article_obj = models.Article.objects.filter(pk=pk).first()

    comment_list = models.Comment.objects.filter(article_id=pk)

    return render(
        request,
        "article_detail.html",
        {
            "username": username,
            "article": article_obj,
            "blog": blog,
            "comment_list":comment_list
         }
    )


def up_down(request):
    print(request.POST)
    print("*"*50)
    article_id = request.POST.get('article_id')
    is_up = json.loads(request.POST.get('is_up'))
    user = request.user
    response = {"status": 1, "msg": ""}
    print("is_up", is_up)
    try:
        models.ArticleUpDown.objects.create(user=user, article_id=article_id, is_up=is_up)
        models.Article.objects.filter(pk=article_id).update(up_count=F("up_count")+1)

    except Exception as e:
        response["status"] = 0
        response["msg"] = models.ArticleUpDown.objects.filter(user=user, article_id=article_id).first().is_up
        print(response["msg"])
    return JsonResponse(response)


def comment(request):
    print(request.POST)

    pid = request.POST.get("pid")
    article_id = request.POST.get("article_id")
    content = request.POST.get("content")
    user_pk = request.user.pk
    print("*"*20)
    print(article_id)
    response = {}
    if not pid:  #根评论
        comment_obj = models.Comment.objects.create(article_id=article_id,user_id=user_pk,content=content)
    else:
        comment_obj = models.Comment.objects.create(article_id=article_id,user_id=user_pk,content=content,parent_comment_id=pid)

    response["create_time"] = comment_obj.create_time.strftime("%Y-%m-%d")
    response["content"] = comment_obj.content
    response["username"] = comment_obj.user.username

    return JsonResponse(response)


def comment_tree(request, article_id):
    ret = list(models.Comment.objects.filter(article_id=article_id).values("pk", "content", "parent_comment_id"))
    print(ret)
    return JsonResponse(ret, safe=False)


def add_article(request):

    if request.method == "POST":
        title = request.POST.get('title')
        article_content = request.POST.get('article_content')
        user = request.user

        bs = BeautifulSoup(article_content,"html.parser")

        # 过滤非法标签
        for tag in bs.find_all():
            print(tag.name)

            if tag.name in ["script", "link"]:
                tag.decompose()

        desc = bs.text[0:150] + "..."

        article_obj = models.Article.objects.create(user=user, title=title, desc=desc)
        models.ArticleDetail.objects.create(content=str(bs), article=article_obj)

        return HttpResponse("添加成功")

    return render(request, "add_article.html")


def upload(request):
    print(request.FILES)
    obj = request.FILES.get("upload_img")

    print("name", obj.name)

    path = os.path.join(settings.MEDIA_ROOT, "add_article_img", obj.name)

    with open(path, "wb") as f:
        for line in obj:
            f.write(line)

    res = {
        "error": 0,
        "url": "/media/add_article_img/"+obj.name
    }

    return HttpResponse(json.dumps(res))

