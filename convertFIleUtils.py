import os
import subprocess
from os import mkdir

inputPath = "/Users/xinggenguo/Downloads/doc_file"
outputPath = "/Users/xinggenguo/Downloads/pdf_file"


def convertDocToPdf(docPath, outPath):
    # file = open(docPath, "w")
    # file.close()
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", docPath, "--outdir", outPath])


if not os.path.exists(inputPath):
    print("inputPath does not exist")
    raise FileNotFoundError("inputPath does not exist")


for file_name in os.listdir(inputPath):
    fileFullPath = os.path.join(inputPath, file_name)
    print(file_name)
    print(fileFullPath)
    file_name, file_ext = os.path.splitext(fileFullPath)
    if not os.path.exists(outputPath):
        mkdir(outputPath)
    # 调用函数
    # docx_to_pdf(fileFullPath, outputFullPath)
    convertDocToPdf(fileFullPath,outputPath)





