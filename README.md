# COMP 3331 Lab Marking Helper

---
This python package consists of few scripts that I have written to make life easier during marking lab submissions. 
It was developed in a *macOS* environment, hence in its current state it will most probably not work on Windows due to 
how path naming works. However, it might work on linux distros (Haven't tested yet).

## How To Use 

---
This package is written with [Python](https://www.python.org/downloads/)(>=3.8). Run the following command to install 
dependencies before using the package. 

### Installation

```
pip install -r requirements.txt
```

### Folder Structure
The script expects the downloaded submissions to be in the following file structure.

```
├── 23T3
│   ├── Assign
│   ├── Lab6
│   │   ├── wed12-clavier
│   │   ├── thu12-clavier
│   │   │   ├── 541xxxx
│   │   │   ├── 541xxxx
│   │   │   │   ├── log
│   │   │   │   └── submission.tar
│   │   │   ├── ...
│   │   │   └── 541xxxx
│   │   └── fri17-organ
│   ├── ...
│   └── Lab1
├── 23T2
│   ├── Assign
│   ├── ...
│   └── Lab1
└──23T1
```
See below figure for more details.

![FileStructure.svg](FileStructure.svg)


## Usage

---
Currently, there are five main functionalities implemented in the package.

1. Check late submissions 
2. Check whether there are new/updated submissions after downloading the file
3. Extract all submission.tar files
4. Remove all extracted files and revert the submission to as it was downloaded
5. Download submissions through SSH from the CSE server 