#flask - gives us all the tools needed to run a flask app by creating an instance of class
#request - allow interaction with HTTP method requests as objects
#jsonify - converts data to JSON
from flask import Flask, request, jsonify
#SQLAlchmy - ORM connect and relate python classes to SQL tables
from flask_sqlalchemy import SQLAlchemy
#marshmallow - allows creation of schems to validate, serialize, and deserialize JSON data
from flask_marshmallow import Marshmallow
#DeclaraitveBase - gives the base model functionality to create the classes as modeel classes for db tables
#Mapped - maps a class attribute to a table, column, or relationship
#mapped_columns -sets column and allows for adding any constraints needed(unique, nullable, primary_key)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey, Table, Column, String, Integer, select, delete, Float
from marshmallow import ValidationError, fields
from typing import List
from datetime import date


#Initialize Flask App
app = Flask(__name__)

#MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI']='mysql+mysqlconnector://root:G0d1sMyJudg3!@localhost/ecommerce_api'

'''There are three major components to this application:
- Models
- Schemas
- API Routes

Databases are the highest level structure, They can contain multiple schemas, views, and tables
Schemas organize related database objectsand contain tables 
Tables represent entities (models), which in this case refer to our python classes'''

#Creating base model which inherits from SQLAlchemy's declarativebase
class Base(DeclarativeBase):
    pass

#Initialize SQLAlchemy and Marshmallow
db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

#==========MODELS===============
class Customer(Base):
    __tablename__ = 'Customer' 

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    email: Mapped[str] = mapped_column(db.String(225))
    address: Mapped[str] = mapped_column(db.String(225))
    
    orders: Mapped[List["Orders"]] = db.relationship(back_populates='customer') 


'''Association Table: order_products
Needed for many to many relationships
This table facilitates the relationship from one order to many products, or many products to one order
Only includes forein keys, creating a complicated class model is unneccessary'''

order_products = db.Table(
    "Order_Products",
    Base.metadata, #Allows this table to locate th foreign keys from the base class
    db.Column('order_id', db.ForeignKey('orders.id')),
    db.Column('product_id', db.ForeignKey('products.id'))
)

class Products(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)
    
    orders: Mapped[List['Orders']] = db.relationship(secondary=order_products, back_populates="products")

class Orders(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)

    customer_id: Mapped[int] =mapped_column(db.ForeignKey('Customer.id'))
    #Creates a many to one relationship to customer table
    customer: Mapped['Customer'] = db.relationship('Customer', back_populates='orders')
    #creating a many-to-many relationship to Products through our association table order_products
    #specifying that this relationsip goes through a secondary table (order_products)
    
    products: Mapped[List['Products']] = db.relationship(secondary=order_products, back_populates="orders")       

#Initialize the database and create tables
with app.app_context():
         db.create_all() #First it checks which tables already exist then creates the tables not found
                    #If table is found with the same name it doesn't construct or modify
                    #DOES NOT MODIFY TABLES. if you want to modify you must drop table and recreate.

#=========SCHEMAS========
'''
Schema - a collection of data base objects, such as tables and views, and describes the structure
of the data and how the various objects relate to one another

Schema uses:
- Validation: When ppl send us info we have to make sure it's valid and complete information
- Deserialization: Translating JSON objects into a Python usable object  or dictionary
- Serialization: Converting Python objects into JSON'''


class CustomerSchema(ma.SQLAlchemyAutoSchema): #Creates schema field based on the SQLAlchemy model passed
    class Meta:
        model = Customer

class ProductSchema(ma.SQLAlchemyAutoSchema): #Creates schema field based on the SQLAlchemy model passed
    class Meta:
        model = Products

class OrderSchema(ma.SQLAlchemyAutoSchema): #Creates schema field based on the SQLAlchemy model passed
    class Meta:
        model = Orders
        include_fk = True #Needed because auto schemas don't auto recogize foreign keys (customer_id)

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


app.route('/')
def home():
    return 'Home'

#===========API CUSTOMER ROUTES========


#Create a new customer using POST request
@app.route('/customers', methods=['POST'])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_customer = Customer(name=customer_data["name"], email=customer_data["email"], address=customer_data["address"])
    db.session.add(new_customer)
    db.session.commit()

    return  jsonify({'Message': 'New customer added successfully', 
                    'customer': customer_schema.dump(new_customer)}), 201

#Get all customers using a GET method
@app.route('/customers', methods=['GET'])
def get_customers():
    try:
        query = select(Customer)
        result = db.session.execute(query).scalars()
        customers = result.all()
        return customers_schema.jsonify(customers), 200
    except ValidationError as e:
        return jsonify(e.messages), 400

#Get individual customer using GET method and dynamic route
@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id): 
    customer = db.session.get(Customer, id)
    return customer_schema.jsonify(customer), 200

#Update a user by ID
@app.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    customer = db.session.get(Customer, id)

    if not customer:
        return jsonify({"Message": "Invalid customer id"}), 400

    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.address = customer_data['address'] 

    db.session.commit()
    return customer_schema.jsonify(customer), 200           

#Delete customer using id
@app.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    customer = db.session.get(Customer, id)

    if not customer:
        return jsonify({"Message": "Invalid customer id"}), 400

    db.session.delete(customer)
    db.session.commit()
    return jsonify({"Message": f"Successfuly deleted customer {id}"})        



#===========API PRODUCT ROUTES========    
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_product = Products(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()

    return jsonify({'Message': "New Product added!",
                    "product": product_schema.dump(new_product)}), 201


#Retrieve all Products
@app.route('/products', methods=['GET'])
def get_products():
    try:
        query = select(Products)
        result = db.session.execute(query).scalars()
        products = result.all()
        return products_schema.jsonify(products), 200
    except ValidationError as e:
        return jsonify(e.messages), 400


#Retrieve a product by order id
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    product = db.session.get(Products, id)
    return product_schema.jsonify(product), 200


#Update a product by ID
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = db.session.get(Products, id)

    if not product:
        return jsonify({"Message": "Invalid product id"}), 400

    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    product.product_name =product_data['product_name']
    product.price = product_data['price']
    

    db.session.commit()
    return product_schema.jsonify(product), 200

#Delete a product by id
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = db.session.get(Products, id)

    if not product:
        return jsonify({"Message": "Invalid product id"}), 400

    db.session.delete(product)
    db.session.commit()
    return jsonify({"Message":f"Successfully deleted product {id}"}), 200               



#===========API ORDER ROUTES========

#Create an ORDER using POST method
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    customer_id = order_data.get('customer_id')
    if not customer_id:
        return jsonify({"Error": "Missing customer_id"}), 400    

    #Retrieve customer id
    customer = db.session.get(Customer, customer_id)     

    #Check if customer exists
    if customer:
        new_order = Orders(order_date=order_data['order_date'], customer_id=order_data['customer_id'])

        db.session.add(new_order)
        db.session.commit()

        return jsonify({'Message': 'New Order Placed!', "order": order_schema.dump(new_order)}), 201

    else:
        return jsonify({"Message": "Invalid customer id"}), 400

#ADD Item to Order
@app.route("/orders/<int:order_id>/add_product/<int:product_id>", methods=['PUT'])
def add_product(order_id, product_id):
    order = db.session.get(Orders, order_id)
    product = db.session.get(Products, product_id)

    if order and product:
        if product not in order.products: #Ensures product isnt already in order
            order.products.append(product) #attaches product to order.products
            db.session.commit() #commits changes to database
            return jsonify({"Message":"Successfully added item to order"}), 200
        else: #product is  in order.products
            return jsonify({"Message": "Item is already included in order"}), 400
    else: #order oro product does not exist
        return jsonify({"Message": "Invalid order id or product id."}), 400   


#Delete a product from an order
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def delete_product_from_order(order_id, product_id):
    order = db.session.get(Orders, order_id)
    product = db.session.get(Products, product_id)

    if order and product:
        if product in order.products: #Ensures product is already in order
            order.products.remove(product) #deletes product from order.products
            db.session.commit() #commits changes to database
            return jsonify({"Message":f"Successfully deleted Product {product_id} from Order {order_id}",
                            "order": order_schema.dump(order)}), 200
        else: #product is not in order.products
            return jsonify({"Message": "Item is not in order"}), 400
    else: #order or product does not exist
        return jsonify({"Message": "Invalid order id or product id."}), 400

#Gets all orders for a user
@app.route('/orders/customer/<int:customer_id>', methods=['GET'])
def get_user_order(customer_id):
    orders = db.session.query(Orders).filter_by(customer_id=customer_id).all()

    if not orders:
        return jsonify({"Message": "No orders found for this customer"}), 400

    return jsonify(orders_schema.dump(orders)), 200 


#Get all products from an order
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_order_products(order_id):
    order = db.session.query(Orders).get(order_id)
    if not order:
        return jsonify({"Message": "Order not found"}), 400

    return jsonify(products_schema.dump(order.products)), 200                                              



if __name__ == '__main__':
    app.run(debug=True)