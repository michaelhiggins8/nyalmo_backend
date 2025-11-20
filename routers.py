from routes.chat_routes.test import router as test_router
from routes.customize_routes.upload_docs import router as upload_docs_router
from routes.customize_routes.serve_document import router as serve_document_router
from routes.customize_routes.delete_documents import router as delete_documents_router
from routes.customize_routes.get_documents import router as get_documents_router
from routes.inbox_routes.make_ruling import router as make_ruling_router
from routes.inbox_routes.fetch_mails import router as fetch_mails_router
from routes.chat_routes.collect_thread import router as collect_thread_router
from routes.chat_routes.delete_thread import router as delete_thread_router
from routes.chat_routes.fetch_threads import router as fetch_threads_router
from routes.billing_routes.make_url import router as make_url_router
from routes.billing_routes.billing_portal import router as billing_portal_router
from routes.billing_routes.check_plan import router as check_plan_router
from routes.billing_routes.check_customer_facts import router as check_customer_facts_router
from routes.auth_routes.check_if_board import router as check_if_board_router
from routes.auth_routes.check_if_subscribed import router as check_if_subscribed_router
from routes.auth_routes.orgid_from_key import router as orgid_from_key_router
from routes.auth_routes.signup import router as signup_router
from routes.auth_routes.signin import router as signin_router
from routes.auth_routes.signout import router as signout_router
from routes.auth_routes.reset_password import router as reset_password_router
from routes.auth_routes.session import router as session_router
from routes.auth_routes.change_password import router as change_password_router
from routes.Rulings_routes.fetch_rulings import router as fetch_rulings_router
from routes.share_routes.get_org_key import router as get_org_key_router
from routes.share_routes.refresh_org_key import router as refresh_org_key_router
routers = [test_router, upload_docs_router, serve_document_router, delete_documents_router, get_documents_router, make_ruling_router, fetch_mails_router, collect_thread_router, delete_thread_router, fetch_threads_router, make_url_router, billing_portal_router, check_plan_router, check_customer_facts_router, check_if_board_router, check_if_subscribed_router, orgid_from_key_router, signup_router, signin_router, signout_router, reset_password_router, session_router, change_password_router, fetch_rulings_router, get_org_key_router, refresh_org_key_router]

