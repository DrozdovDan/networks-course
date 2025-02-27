import json
import flask
from flask import Flask, request, jsonify, send_file

last_product_id = -1


class Product:

    def __init__(self, name, description, icon=None):
        global last_product_id
        last_product_id += 1

        self.id = last_product_id
        self.name = name
        self.description = description
        self.icon = icon

    def __iter__(self):
        yield 'id', self.id
        yield 'name', self.name
        yield 'description', self.description
        if self.icon:
            yield 'icon', self.icon

    def set_field(self, name, field):
        if name == 'name':
            self.name = field
        elif name == 'description':
            self.description = field
        elif name == 'icon':
            self.icon = field

    def get_image(self):
        return self.icon


app = Flask(__name__)

products = dict()


@app.route('/product', methods=['POST'])
def create_product():
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    try:
        product = Product(data['name'], data['description'])
    except KeyError:
        return jsonify({'error': 'Missing required field'}), 400

    products[product.id] = product

    return jsonify(product.__dict__)


@app.route('/product/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        id = int(product_id)
    except ValueError:
        return jsonify({'error': 'Invalid product id'}), 400
    if id not in products:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify(products[id].__dict__)


@app.route('/product/<product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    try:
        id = int(product_id)
    except ValueError:
        return jsonify({'error': 'Invalid product id'}), 400
    if id not in products:
        return jsonify({'error': 'Product not found'}), 404

    for field in data.keys():
        if field not in products[id].__dict__.keys() or field == 'id':
            return jsonify({'error': 'Invalid field'}), 400

    for field in data.keys():
        products[id].set_field(field, data[field])

    return jsonify(products[id].__dict__)


@app.route('/product/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        id = int(product_id)
    except ValueError:
        return jsonify({'error': 'Invalid product id'}), 400
    if id not in products:
        return jsonify({'error': 'Product not found'}), 404

    product = products[id]
    del products[id]

    return jsonify(product.__dict__)


@app.route('/products', methods=['GET'])
def get_all():
    return jsonify(list(map(lambda x: x.__dict__, products.values())))


@app.route('/product/<product_id>/image', methods=['POST'])
def upload_image(product_id):
    try:
        id = int(product_id)
    except ValueError:
        return jsonify({'error': 'Invalid product id'}), 400

    if id not in products:
        return jsonify({'error': 'Product not found'}), 404

    product = products[id]

    try:
        file = request.files['icon']
        file.save(f'{product_id}.png')
    except KeyError:
        return jsonify({'error': 'Missing required field'}), 400

    product.icon = f'{product_id}.png'

    return jsonify({'image': f'{product_id}.png'}), 200


@app.route('/product/<product_id>/image', methods=['GET'])
def get_image(product_id):
    try:
        id = int(product_id)
    except ValueError:
        return jsonify({'error': 'Invalid product id'}), 400

    if id not in products:
        return jsonify({'error': 'Product not found'}), 404

    product = products[id]

    if not product.icon:
        return jsonify({'error': 'Icon not found'}), 404

    return send_file(product.icon, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
