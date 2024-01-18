import os


def find_file(search_folder, file_name):
    """
    Recursively checks through folders to identify the location of the file with the name "file_name". Will only search
    for files with the extensions .py, .java, and .c. If no file with a matching file name is found, the function will
    return None, else the path to the file will be returned.

    :param search_folder: Path of the top directory to be searched in
    :param file_name: Name of the file to be searched, without the extension
    :return: Path of the file if found
    """

    current_files = os.listdir(search_folder)
    lang_map = {
        ".py": "Python",
        ".java": "Java",
        ".c": "C"
    }
    directories = []

    for directory in current_files:
        current_file_name, current_file_ext = os.path.splitext(directory)
        if current_file_name == file_name:
            if current_file_ext in [".py", ".c", ".java"]:
                return {"folder_path": search_folder, "ext": current_file_ext, "language": lang_map[current_file_ext]}
        else:
            temp_path = os.path.join(search_folder, directory)
            if os.path.isdir(temp_path):
                directories.append(temp_path)

    for directory in directories:
        return find_file(directory, file_name)

    return None
