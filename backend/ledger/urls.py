from django.urls import path

from . import views

urlpatterns = [
    path("accounts/", views.AccountListCreateView.as_view()),
    path("transfers/", views.TransferView.as_view()),
    path("deposits/", views.DepositView.as_view()),
    path("statements/", views.StatementImportView.as_view()),
    path("transactions/search/", views.TransactionSearchView.as_view()),
]
