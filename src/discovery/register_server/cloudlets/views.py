from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import generic
from .util.utils import ObjectRange, RangeNotSatisfiable, paginate

from cloudlets.models import Cloudlet


def index(request):
    return render(request, "cloudlets/index.html", {})



@login_required
def all_images(request):
    info = UserInfo.objects.get_or_create(user=request.user)[0]
    return paginate(request, 'archive/all-images.html',
            Cloudlet.objects.all(),
            feed_token=info.feed_token)


class CloudletListView(generic.ListView):
    template_name = 'cloudlets/cloudlet_list.html'
    context_object_name = 'latest_cloudlet_list'

    def get_queryset(self):
        return Cloudlet.objects.order_by('-mod_time')


class CloudletDetailsView(generic.DetailView):
    model = Cloudlet
    template_name = 'cloudlets/cloudlet_details.html'


