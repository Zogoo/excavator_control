# -*- coding: utf-8 -*-
# オープンデータをGoogle AutoMLで利用できるようにする
# (PascalVoc形式 XML から Google AutoML 用のCSVを作成する)

#---------------------------------------------------------------------
# ユーザー設定値
#---------------------------------------------------------------------

# フォルダパス (ローカルPC内で PascalVoc形式XMLが格納されているフォルダ)
from tkinter import Tk, messagebox
import xml.etree.ElementTree as ET
import itertools
import glob
import os.path
import sys
xmlFolderPath = './'

# フォルダパス (ローカルPC内で 画像ファイルが格納されているフォルダ)
imgFolderPath = './'

# フォルダパス (GoogleCloudStorage内で、画像ファイルを格納しているフォルダ)
imgFolderPath_gs = 'gs://toy_shovel_car/shovel_pics/'

# CSV出力パス
outputCSVpath = 'AutoMLVision.csv'

# CSV出力時の座標の桁数 (小数点以下何桁まで出力するか)
roundDigit = 2


#---------------------------------------------------------------------
# ライブラリの読み込み
#---------------------------------------------------------------------


#---------------------------------------------------------------------
# メッセージボックスの表示
#---------------------------------------------------------------------
def MBox(msg):

	# Tkを定義
	root = Tk()
	root.withdraw()  # Tkのrootウインドウを表示しない

	# コンソール表示
	print('\n' + msg + '\n')

	# メッセージボックスの表示
	messagebox.showerror(os.path.basename(__file__), msg)


#---------------------------------------------------------------------
# エラー終了 (コンソールとメッセージボックスでエラー内容を通知して終了)
#---------------------------------------------------------------------
def ErrorEnd(msg):

    # メッセージボックスを表示
	MBox(msg)

	# プロセス終了
	sys.exit()


#---------------------------------------------------------------------
# メイン
#---------------------------------------------------------------------
print('--- Process Start --------------------------------')

# フォルダの存在確認 (アノテーションファイル格納フォルダ)
xmlFolderPath = os.path.abspath(xmlFolderPath)
if(os.path.exists(xmlFolderPath) == False):
    ErrorEnd('Error | 指定された入力フォルダが存在しません: ' + xmlFolderPath)

# フォルダの存在確認 (画像格納フォルダ)
imgFolderPath = os.path.abspath(imgFolderPath)
if(os.path.exists(imgFolderPath) == False):
    ErrorEnd('Error | 指定された入力フォルダが存在しません: ' + imgFolderPath)

# ファイル数の一致を確認 (アノテーションファイルと画像ファイル)
anoFilePaths = glob.glob(xmlFolderPath + '/*.xml')
imgFilePaths = glob.glob(imgFolderPath + '/*.jpg')
if(len(anoFilePaths) != len(imgFilePaths)):
    s = 'Error | アノテーションファイルと画像ファイルの数が一致していません'
    s = s + '\n' + str(len(anoFilePaths)) + ' Annotation Files'
    s = s + '\n' + str(len(anoFilePaths)) + ' Image Files'
    ErrorEnd(s)

# ファイルの対応を確認 (# アノテーションファイル名が AAA.xml の場合、AAA.jpgという画像があるか確認)
for i in range(len(anoFilePaths)):
    n1 = os.path.basename(anoFilePaths[i])
    n1 = os.path.splitext(n1)[0]
    for j in range(len(imgFilePaths)):
        n2 = os.path.basename(imgFilePaths[j])
        n2 = os.path.splitext(n2)[0]
        if(n1 == n2):
            b = True
            break
    else:
        ErrorEnd('Error | アノテーションファイルに対応する画像ファイルが見つかりませんでした: ' + n1 + '.xml')

# アノテーションファイルの読み取り
outputLines = []
for i, anoFilePath in enumerate(anoFilePaths):

    # アノテーションファイルのパス取得
    anoFilePath = os.path.abspath(anoFilePath)
    print(str(i) + '/' + str(len(anoFilePaths)) + ': ' + anoFilePath)

    # アノテーションファイルを開く
    anoFile = open(anoFilePath)

    # アノテーションファイル内のデータを取得 (ルート要素)
    anoRoot = (ET.parse(anoFile)).getroot()

    # アノテーションファイル内のデータを取得 (画像ファイル名、横幅、縦幅)
    imgFileName = anoRoot.find('filename')
    width = anoRoot.find('size/width')
    height = anoRoot.find('size/height')

    if imgFileName is None:
        ErrorEnd('Error | XMLファイル内で annotation/filename が見つかりませんでした' + anoFilePath)
    if imgFileName is None:
        ErrorEnd('Error | XMLファイル内で annotation/size/width が見つかりませんでした' + anoFilePath)
    if imgFileName is None:
        ErrorEnd(
            'Error | XMLファイル内で annotation/size/height が見つかりませんでした' + anoFilePath)

    imgFileName = imgFileName.text
    width = width.text
    height = height.text

    # path要素からファイル名を取得するパターン (filenameに拡張子が記載されていない時のための処理)
    #imgFileName = anoRoot.find('path')
    #if imgFileName is None :
    #    ErrorEnd('Error | XMLファイル内で annotation/path が見つかりませんでした' + anoFilePath)
    #imgFileName = os.path.basename(imgFileName)

    # アノテーションファイル名が AAA.xml の場合、ファイル内にAAA.jpgと書いてあることを確認
    if(os.path.splitext(os.path.basename(anoFilePath))[0] != os.path.splitext(os.path.basename(imgFileName))[0]):
        ErrorEnd(
            'Error | XMLファイル名と XMLファイル内に書き込まれている画像ファイルの名称が一致していません' + anoFilePath)

    # アノテーションファイル内のデータを取得 (オブジェクト)
    for j, obj in enumerate(anoRoot.iter('object')):

        # アノテーションファイル内のデータを取得 (各オブジェクトのタグ・左上座標・右下座標)
        label = obj.find('name')
        xMin = obj.find('bndbox/xmin')
        yMin = obj.find('bndbox/ymin')
        xMax = obj.find('bndbox/xmax')
        yMax = obj.find('bndbox/ymax')

        if label is None:
            ErrorEnd(
            	'Error | XMLファイル内に object/name が存在しないオブジェクトが存在します' + anoFilePath)
        if xMin is None:
            ErrorEnd(
            	'Error | XMLファイル内に object/bndbox/xmin が存在しないオブジェクトが存在します' + anoFilePath)
        if yMin is None:
            ErrorEnd(
            	'Error | XMLファイル内に object/bndbox/ymin が存在しないオブジェクトが存在します' + anoFilePath)
        if xMax is None:
            ErrorEnd(
            	'Error | XMLファイル内に object/bndbox/xmax が存在しないオブジェクトが存在します' + anoFilePath)
        if yMax is None:
            ErrorEnd(
            	'Error | XMLファイル内に object/bndbox/ymax が存在しないオブジェクトが存在します' + anoFilePath)

        label = label.text
        xMin = xMin.text
        yMin = yMin.text
        xMax = xMax.text
        yMax = yMax.text

        # 座標変換 (Pascal Voc形式 から AutoML Vision形式へ)
        xMinRatio = round(int(xMin) / int(width),  roundDigit)
        yMinRatio = round(int(yMin) / int(height), roundDigit)
        xMaxRatio = round(int(xMax) / int(width),  roundDigit)
        yMaxRatio = round(int(yMax) / int(height), roundDigit)

        # データの区分を設定 (アノテーションファイルの80%はテスト用、10%はバリデーション用、10%はテスト用)
        datasetName = 'TRAIN'
        if (0.8 < (i/len(anoFilePaths))):
            datasetName = 'VALIDATE'
        if (0.9 < (i/len(anoFilePaths))):
            datasetName = 'TEST'

        # 出力文字列の作成 (AutoML Vision形式)
        formatString = '{0:.' + str(roundDigit) + 'f}'
        sOutput = datasetName
        sOutput = sOutput + ',' + imgFolderPath_gs + imgFileName
        sOutput = sOutput + ',' + label
        sOutput = sOutput + ',' + formatString.format(xMinRatio)
        sOutput = sOutput + ',' + formatString.format(yMinRatio)
        sOutput = sOutput + ',,'
        sOutput = sOutput + ',' + formatString.format(xMaxRatio)
        sOutput = sOutput + ',' + formatString.format(yMaxRatio)
        sOutput = sOutput + ',,'
        outputLines.append(sOutput)

        # 出力文字列の例
        # set,path,label,x_min,y_min,,,x_max,y_max,,
        # TRAIN,gs://cloud-ml-data/img/openimage/2851/11476419305_7b73a0128c_o.jpg,Baked goods,0.56,0.25,,,0.97,0.50,,

    # アノテーションファイルを閉じる
    anoFile.close()

# ファイル出力 (AutoML Vision形式CSV)
outputCSVpath = os.path.abspath(outputCSVpath)
try:
    with open(outputCSVpath, mode='w') as f:
        for line in outputLines:
            f.write(line + '\n')
except Exception as e:
    ErrorEnd('Error | ファイル出力に失敗しました: ' + str(e))

# 終了通知
MBox('正常終了しました。\n出力ファイル: ' + outputCSVpath)

#---------------------------------------------------------------------
# End
