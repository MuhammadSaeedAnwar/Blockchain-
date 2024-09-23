import hashlib
import json
from time import time
import pandas as pd
import os

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []

        # Load the blockchain from the CSV file if it exists
        self.load_chain()

    def new_block(self, proof, previous_hash=None):
        index = len(self.chain)
        block = {
            'index': index,
            'timestamp': time(),
            'transactions': self.pending_transactions.copy(),
            'proof': proof,
            'previous_hash': previous_hash or (self.hash(self.chain[-1]) if self.chain else '0'),
        }

        self.pending_transactions = []
        self.chain.append(block)

        # Save the updated chain to the CSV file
        self.save_chain()

        return block

    def new_transaction(self, name, reg_no, marks, description, total_marks):
        # Validate all fields are provided
        if not all([name, reg_no, marks, description, total_marks]):
            raise ValueError("All transaction fields (name, reg_no, marks, description, total_marks) must be provided")
        
        transaction = {
            'name': name,
            'reg_no': reg_no,
            'marks': marks,
            'total_marks': total_marks,
            'description': description
        }

        if name and reg_no:
            self.pending_transactions.append(transaction)
            return self.last_block['index'] + 1 if self.chain else 0

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1] if self.chain else None

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def save_chain(self):
        # Convert the chain to a DataFrame
        df = pd.DataFrame([{
            'index': block['index'],
            'timestamp': block['timestamp'],
            'transactions': json.dumps(block['transactions']),  # Convert transactions to JSON string
            'proof': block['proof'],
            'previous_hash': block['previous_hash']
        } for block in self.chain])
        # Save the DataFrame to a CSV file
        df.to_csv('blockchain.csv', index=False)
        # Log transactions for debugging
        with open('Log.txt', 'a') as file:
            for block in self.chain:
                file.write(f"{block['transactions']}\n")

    def load_chain(self):
        if not os.path.exists('blockchain.csv'):
            return

        # Load the chain from the CSV file into a DataFrame
        df = pd.read_csv('blockchain.csv')
        for _, row in df.iterrows():
            block = {
                'index': int(row['index']),
                'timestamp': float(row['timestamp']),
                'transactions': json.loads(row['transactions']),  # Convert JSON string to list
                'proof': int(row['proof']),
                'previous_hash': row['previous_hash']
            }
            self.chain.append(block)


blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student')
def student():
    return render_template('student.html')

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['name', 'reg_no', 'marks', 'description', 'total_marks']
    if not all(k in values for k in required):
        return 'Missing values', 400
    index = blockchain.new_transaction(values['name'], values['reg_no'], values['marks'], values['description'], values['total_marks'])
    response = {
        'message': f'Transaction will be added to Block {index}',
        'transaction': {
            'name': values['name'],
            'reg_no': values['reg_no'],
            'marks': values['marks'],
            'description': values['description'],
            'total_marks': values['total_marks']
        }
    }
    return jsonify(response), 201


@app.route('/mine', methods=['GET'])
def mine():
    # Check if there are pending transactions to mine
    if not blockchain.pending_transactions:
        return jsonify({'message': 'No transactions to mine.'}), 400

    # Gather data from pending transactions to include in the new block
    last_block = blockchain.last_block
    last_proof = last_block['proof'] if last_block else 0
    proof = blockchain.proof_of_work(last_proof)

    # Create a new block with the proof and previous hash
    previous_hash = blockchain.hash(last_block) if last_block else None
    block = blockchain.new_block(proof, previous_hash)

    return jsonify({'message': 'New block forged.', 'block': block}), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/student/<reg_no>', methods=['GET'])
def get_student_info(reg_no):
    student_blocks = []
    total_marks = 0
    for block in blockchain.chain:
        for transaction in block['transactions']:
            if transaction['reg_no'] == reg_no:
                student_blocks.append(transaction)
                total_marks += int(transaction['marks'])
    if student_blocks:
        return jsonify({'blocks': student_blocks, 'total_marks': total_marks}), 200
    return jsonify({'message': 'Student not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

