# Inventory Management System

## Overview
The Inventory Management System (IMS) is a web application built using Flask. It allows users to manage products, categories, orders, and user activities efficiently.

## Features
- **User Management**: Admins can add, edit, and delete users. User roles include Admin, Manager, Supervisor, and User.
- **Product Management**: Users can view, add, edit, and delete products. The system tracks stock levels and alerts for low stock.
- **Order Management**: Users can create and manage orders, with tracking for order status.
- **Reporting**: The application provides various reports, including inventory value, usage trends, and expenditure summaries.
- **Data Visualization**: Charts for usage and expenditure trends are generated using Chart.js.

## Technologies Used
- **Backend**: 
  - Flask (Python)
  - SQLAlchemy for database management
  - Flask-Login for user authentication

## Installation
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd inventory-management
   ```
3. Set up the Python environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
- Start the Flask application:
  ```bash
  python app.py
  ```
- Access the application in your web browser at `http://localhost:5000`.

## Contributing
Feel free to submit issues or pull requests for improvements and bug fixes.

## License
This project is licensed under the MIT License.
