# Importa todos os modelos para que o SQLAlchemy conheça as tabelas.
# Ao criar um módulo novo, adicione o import do modelo aqui.
from app.models.user_model import Producer  # noqa: F401
from app.models.product_model import Product, ProductImage  # noqa: F401
from app.models.admin_model import Admin  # noqa: F401
from app.models.review_model import Review  # noqa: F401
from app.models.order_model import Order, OrderItem, PremiumSubscription  # noqa: F401
from app.models.cost_model import CostCalculation  # noqa: F401
