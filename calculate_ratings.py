from DataManager import DataManager

def main():
    data_manager = DataManager()
    data_manager.calculate_ratings()
    data_manager.update_data_files()

if __name__ == "__main__":
    main()
