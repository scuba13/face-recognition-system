from linha.db.handler import MongoDBHandler

def main():
    db = MongoDBHandler()
    db.list_employees()

if __name__ == "__main__":
    main() 