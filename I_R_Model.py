# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 10:56:20 2025

@author: Leoni
"""

import pandas as pd
import matplotlib as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter
from tkinter import ttk
from collections import defaultdict

def InflitrationModel():
    """ Hier Funktion erklären """
    
    def RunSimulation():
        
        # progressbar danmit man sieht das was passiert
        nonlocal mainWindow
        progressbar = ttk.Progressbar(mainWindow)
        progressbar.place(anchor="sw", relwidth=1, relx=0, rely=1)
        progressbar.step(0)
        progressbarCurrentState = 0
        mainWindow.update()
        
        # alle datensätze zurücksetzten, damit keine überesste von vorheriger simulation probleme bereiten
        nonlocal outputdata
        outputdata = pd.DataFrame()
        nonlocal layer1WaterDistribution
        layer1WaterDistribution = defaultdict(dict)
        nonlocal layer1WaterDistributionPercent
        layer1WaterDistributionPercent = pd.DataFrame()
        
        
        inputFileName = filePathBox.get()
        inputSeperator = inputSeperatorBox.get()
        inputColumnName = inputColumnNameBox.get()
        try:
            inputUnitFactor = float(inputUnitFactorBox.get())
        except:
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: Failed to convert data with the "Unit Correction Factor" provided. Did you use a "," as the decimal seperator?', wraplength=230)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        
        try: # Parameter für das layer
            thickness1 = float(inputLayer1ThicknessBox.get()) # storage vom layer ist Tickness * Porosity[mm] 
            hydraulicCon1 = float(inputLayer1HydraulicConBox.get()) # [mm/min]
            porosity1 = float(inputLayer1PorosityBox.get())   # [Vol/Vol]
            initialWatercontent1 = float(inputLayer1InitialH2OBox.get()) # [Vol/Vol]
            fieldCapacity1 = float(inputLayer1FieldKapacityBox.get()) # [Vol/Vol]
            if initialWatercontent1 > porosity1 or fieldCapacity1 > porosity1:
                inputPopup = tkinter.Toplevel(mainWindow)
                inputPopup.title("ERROR")
                inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: The Initial water content and Field Capacity cannot be larger then the porosity.', wraplength=200)
                inputPopupLabel.pack(padx=30, pady=30)
                progressbar.destroy()
                return
        except:
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: Failed to read "Upper Layer Parameters" provided. Did you use a "," as the decimal seperator?', wraplength=200)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        try: # Parameter für das untere Model Boundary
            HydraulicConacity2 = float(inputlayer2HydraulicConBox.get()) # [mm/min]
            maxSufacePonding = float(inputMaxPondingBox.get())   # [mm]
            evaporation = float(inputEvaporationBox.get()) # [mm/min]
            
        except:
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: Failed to read "Model Boundary Parameters" provided. Did you use a "," as the decimal seperator?', wraplength=200)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        ###############################################################################
        # datenbanken einlesen und output vorbereiten
        
        # Datei einlesen mit Trennzeichen
        try:
            inputdata = pd.read_csv(inputFileName, sep=inputSeperator, encoding='latin1')
        except:
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: The function "read_CSV" in the package "pandas" cannot open the file with the given parameters.', wraplength=200)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        progressbar.configure(maximum=(len(inputdata.index)*1.1))
        progressbar.step(1)
        progressbarCurrentState = 1
        mainWindow.update()
        
        #Neuen df machen - für die output sachen
        try:
            outputdata["Intensity"] = inputdata[inputColumnName] * inputUnitFactor
            outputdata["Surface Infiltration"] = "" # die sind hier auch drinne damit es übersichtlicher ist
            outputdata["Runoff"] = ""
            outputdata["Current Surface Ponding"] = ""
            outputdata["Lower Layer Infiltration"] = ""
            outputdata["Evaporation"] = ""
            outputdata["Control Sum of Sublayer Storage"] = ""
            outputdata["Sum of Sublayer Storage"] = ""
        except:
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: Cannot find the column name provided in "Column with [intensity/min] Data".', wraplength=200)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        outputdata.index = outputdata.index + 1 # indexe verschieben damit bei der verarbeitung in der simulation von 1 angefagen werden kann (dannbrauch es keine spezielle if qualifier für die erste oder letzte zeile)
        
        
        ###############################################################################
        # funktionen definieren
        
        
        def LogSurfaceInteractions(currentSurfaceInfiltration): # infiltrationsfunktion innerhalb der simulationsfunktion um variablenzugriff zu vereinfachen
            
            nonlocal currentLayer1Storage
            currentLayer1Storage = currentLayer1Storage + currentSurfaceInfiltration
            nonlocal currentSurfacePonding
            currentSurfacePonding = currentSurfacePonding - currentSurfaceInfiltration
            
            nonlocal runOff
            if currentSurfacePonding > maxSufacePonding: # runnoff berechnen
                runOff = currentSurfacePonding - maxSufacePonding
                currentSurfacePonding = maxSufacePonding
            else:
                runOff = 0
                
            # alle daten speichern, wird hier alles auf einnmal gemacht um die zugriffe auf den dataframe zu minimieren damit es schneller läuft
            outputdata.loc[timeIndex] = [outputdata.at[timeIndex,"Intensity"], currentSurfaceInfiltration, runOff, currentSurfacePonding, currentLowerLayerInfiltration, currentEvaporation, currentLayer1Storage, sum(layer1WaterDistribution[timeIndex].values())]
                
            
            
        def MoveFullWettingFrontDown(newFullWettingFrontPosition):
            nonlocal newFullWettingFront
            while layer1WaterDistribution[timeIndex][newFullWettingFrontPosition] >= hydraulicCon1:
                newFullWettingFront = newFullWettingFrontPosition
                newFullWettingFrontPosition = newFullWettingFrontPosition+1
        
        
        ###############################################################################
        # initialwerte berechnen und setzten
        
        
        sublayerThickness1 = hydraulicCon1/porosity1
        sublayerCount1 = round(thickness1 / (sublayerThickness1)) # sublayer dicke so festlegen, dass pro minute immer eine schicht weiter geht (=haydraulic konductivity in [mm/min])
        if sublayerCount1 < 3: # testen ob zu wenige su layer da sind, wenn ja: abbruch
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: The amount of sublayer resulting from the current inputs for the upper layer is below 3. This tool requires at least 3 Sublayers. The thickness of the sublayers is calculated as the distance water can travel within the soil over one minute by [Hydraulic Conductivity / Porosity]. The amount of sublayers then results from [Thickness of the upper layer / Thickness of the sublayers].', wraplength=360)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        initialSublayerWatercontent1 = (sublayerThickness1) * initialWatercontent1 # konvertieren von Vol/Vol in mm wasser pro schicht
        fieldCapacity1 = (sublayerThickness1) * fieldCapacity1 # konvertieren von Vol/Vol in mm wasser pro schicht
        
        #Dictionary of Dictionary's:
        layer1WaterDistribution[0] = dict.fromkeys(range(sublayerCount1), initialSublayerWatercontent1)
        
        ### initialwerte
        timeIndex = 1
        currentSurfacePonding = 0
        previousTimeStepLeftover = 0
        waterToBeMoved = 0
        newFullWettingFront = -1 # die neuste gesättigte nassfront "schiebt" die fieldcapacity vor sich her damit die maximal angegeben infiltration erreicht wird (sonnst ist das maximum: max infiltration - field capcity)
        currentLayer1Storage = thickness1 * initialWatercontent1
        currentLowerLayerInfiltration = 0
        runOff = 0
        currentEvaporation = 0
        previosSublayer0Leftover = initialSublayerWatercontent1
        progressbarStep = round(len(inputdata.index)*0.05)
        
        
        ####################################################################################
        ### Simulations Loop
        
        
        print("Starting Simulation")
        for inputIntensity in outputdata["Intensity"]:
            
            if timeIndex == progressbarCurrentState + progressbarStep: # es ist schneller die nur alle 100 schritte zu aktualisieren weil mainwindow.update() sehr langsam ist
                progressbar.step(progressbarStep)
                progressbarCurrentState = progressbarCurrentState + progressbarStep
                mainWindow.update()
                
                
            ####################################################################################
            ### Wie viel Wasser versickert vom untersten Sublayer in das 2. Layer.
            
            
            # unterstes sublayer berechen
            if layer1WaterDistribution[timeIndex-1][sublayerCount1-1] <= fieldCapacity1: # wenn das Wasser unterhalb der field capacity is mache nix
                previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][sublayerCount1-1]
                currentLowerLayerInfiltration = 0
            elif layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - fieldCapacity1 < HydraulicConacity2: # wenn weniger infiltrieren kann als maximal (Hydraulic Conductivity 2) möglich
                previousTimeStepLeftover = fieldCapacity1
                currentLowerLayerInfiltration = layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - fieldCapacity1
                currentLayer1Storage = currentLayer1Storage - (layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - fieldCapacity1)
            else: # wenn mehr infiltrieren kann als maximal (Hydraulic Conductivity 2) möglich
                previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - HydraulicConacity2
                currentLowerLayerInfiltration = HydraulicConacity2
                currentLayer1Storage = currentLayer1Storage - HydraulicConacity2
           
            
            ####################################################################################
            # durch alle "normalen" sublayer durch ittereieren
            
            
            for subLayerIndex in reversed(range(2, sublayerCount1)): # reversed range damit von unten nach ob (sonnst "wellen" und weniger bewegung)
                
                if newFullWettingFront >= subLayerIndex-2: # wenn zwei layer drüber die neuste gesättigte nassfront ist
                    waterToBeMoved = layer1WaterDistribution[timeIndex-1][subLayerIndex-1]
                    if previousTimeStepLeftover + waterToBeMoved >= hydraulicCon1: # wenn wir nich alles aufnehmen können weil unser layer schon viel hat
                        layer1WaterDistribution[timeIndex][subLayerIndex] = hydraulicCon1
                        previousTimeStepLeftover = waterToBeMoved - (hydraulicCon1 - previousTimeStepLeftover)
                        if newFullWettingFront == subLayerIndex-2 or newFullWettingFront == subLayerIndex-1: # auf uns oder tiefer verschieben falls sie gerade über uns war
                            MoveFullWettingFrontDown(subLayerIndex)
                    else: # wenn alles bei uns rein passt und kleiner is als hydraulic conductivity
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover + waterToBeMoved
                        previousTimeStepLeftover = 0
                        
                elif layer1WaterDistribution[timeIndex-1][subLayerIndex-1] > fieldCapacity1: # wenn ein layer drüber mehr drinne hat als field capacity
                    waterToBeMoved = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] - fieldCapacity1
                    if previousTimeStepLeftover + waterToBeMoved > hydraulicCon1: # wenn wir nich alles aufnehmen können weil unser layer schon viel hat
                        layer1WaterDistribution[timeIndex][subLayerIndex] = hydraulicCon1
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] - (hydraulicCon1 - previousTimeStepLeftover)
                    else: # wenn alles ins nächste layer passt
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover + waterToBeMoved
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] - waterToBeMoved
                else: # wenn ein layer drüber weniger als die field capacity ist
                    if previousTimeStepLeftover >= fieldCapacity1: # wenn unser layer mit leftover voller is als field capacity
                        waterToBeMoved = (fieldCapacity1 - layer1WaterDistribution[timeIndex-1][subLayerIndex-1]) / 2
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover - waterToBeMoved
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] + waterToBeMoved
                    else: # wenn unser layer auch weniger hat as fieldcapacity
                        waterToBeMoved = (previousTimeStepLeftover - layer1WaterDistribution[timeIndex-1][subLayerIndex-1]) / 2
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover - waterToBeMoved
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] + waterToBeMoved
                        
                        
            ####################################################################################
            # 1. und 2. sublayer + infiltration + evaporation + neuste gesättigte nassfront erstellen/beenden
            
            
            currentSurfacePonding = currentSurfacePonding + inputIntensity # wie viel wassersteht diese minute zum inflitrieren bereit
            if currentSurfacePonding >= evaporation: # wenn genug da is um aus dem ponding zu verdunsten
                currentSurfacePonding = currentSurfacePonding - evaporation
                currentEvaporation = evaporation
                previosSublayer0Leftover = layer1WaterDistribution[timeIndex-1][0]
            elif layer1WaterDistribution[timeIndex-1][0] + currentSurfacePonding > evaporation:
                previosSublayer0Leftover = layer1WaterDistribution[timeIndex-1][0] - (evaporation - currentSurfacePonding)
                currentLayer1Storage = currentLayer1Storage - (evaporation - currentSurfacePonding)
                currentSurfacePonding = 0
                currentEvaporation = evaporation
            else:
                currentEvaporation = layer1WaterDistribution[timeIndex-1][0] + currentSurfacePonding
                currentLayer1Storage = currentLayer1Storage - layer1WaterDistribution[timeIndex-1][0]
                currentSurfacePonding = 0
                previosSublayer0Leftover = 0
            
            
            
            
            if newFullWettingFront == -1: # wenn gerade keine gesättigte nassfront unterwegs ist
                # gucken was sich bewegen sollte, unabhängig vom ponding
                if previosSublayer0Leftover > fieldCapacity1:  # wenn im obersten sublayer mehr drinne hat als field capacity
                    waterToBeMoved = previosSublayer0Leftover - fieldCapacity1
                    if previousTimeStepLeftover + waterToBeMoved >= hydraulicCon1: # wenn nich alles bei uns reinpasst
                        waterToBeMoved = waterToBeMoved - (previousTimeStepLeftover + waterToBeMoved - hydraulicCon1)                    
                elif previousTimeStepLeftover >= fieldCapacity1: # wenn im obersten sublayer weniger als die field capacity ist und unser layer mit leftover voller is als field capacity
                    waterToBeMoved = (previosSublayer0Leftover - fieldCapacity1) / 2
                else: # wenn unser layer auch weniger hat as fieldcapacity
                    waterToBeMoved = (previosSublayer0Leftover - previousTimeStepLeftover) / 2
                
                # ensteht eine neue gesättigte nassfront?
                if currentSurfacePonding + previosSublayer0Leftover - waterToBeMoved >= hydraulicCon1: # Ja: wenn wir erwarten, dass das oberste sublayer voll ist (unter berücksichtigung von dem dem wasser was sich bewegen sollte)
                    if currentSurfacePonding + previosSublayer0Leftover <= hydraulicCon1: # wenn capilary rise für die überfüllung sorgt
                        layer1WaterDistribution[timeIndex][1] = previousTimeStepLeftover
                        layer1WaterDistribution[timeIndex][0] = currentSurfacePonding + previosSublayer0Leftover
                        LogSurfaceInteractions(currentSurfacePonding) # übergib die veränderung am surface ponding
                    else:
                        #  wie viel sich aus dem 1. ins 2. sublayer bewegen müsste damit es passt
                        if currentSurfacePonding >= hydraulicCon1: # wenn das current surfcae ponding sehr viel ist
                            waterToBeMoved = previosSublayer0Leftover
                        else: # wenn das current surfcae ponding nicht so viel ist
                            waterToBeMoved = previosSublayer0Leftover - (hydraulicCon1 - currentSurfacePonding)
                        if previousTimeStepLeftover + waterToBeMoved < hydraulicCon1: # es passt alles ins 2. sublayer
                            layer1WaterDistribution[timeIndex][1] = previousTimeStepLeftover + waterToBeMoved
                            layer1WaterDistribution[timeIndex][0] = hydraulicCon1
                            newFullWettingFront = 0
                            if currentSurfacePonding >= hydraulicCon1:
                                LogSurfaceInteractions(hydraulicCon1) # übergib die veränderung am surface ponding
                            else:
                                LogSurfaceInteractions(currentSurfacePonding) # übergib die veränderung am surface ponding
                        else: # wenn nich alles ins 1. und 2. sublayer passt
                            layer1WaterDistribution[timeIndex][1] = hydraulicCon1
                            layer1WaterDistribution[timeIndex][0] = hydraulicCon1
                            MoveFullWettingFrontDown(1)
                            LogSurfaceInteractions(hydraulicCon1 - previosSublayer0Leftover + (hydraulicCon1 - previousTimeStepLeftover)) # übergib die veränderung am surface ponding
                else: # Nein: das oberste sublayer wird nicht voll, alles kann infiltrieren
                    layer1WaterDistribution[timeIndex][1] = previousTimeStepLeftover + waterToBeMoved
                    layer1WaterDistribution[timeIndex][0] = previosSublayer0Leftover - waterToBeMoved + currentSurfacePonding
                    LogSurfaceInteractions(currentSurfacePonding) # übergib die veränderung am surface ponding
            elif newFullWettingFront >= 0: # wenn schon eine gesättigte nassfront unterwegs ist
                if currentSurfacePonding + previousTimeStepLeftover >= hydraulicCon1: # und es kommt genug wasser nach um sie zu erhalten
                    layer1WaterDistribution[timeIndex][1] = hydraulicCon1
                    layer1WaterDistribution[timeIndex][0] = hydraulicCon1
                    LogSurfaceInteractions(hydraulicCon1 - previousTimeStepLeftover) # übergib die veränderung am surface ponding
                    if newFullWettingFront == 0 or newFullWettingFront == 1: # auf uns oder tiefer verschieben falls sie gerade über uns war
                        MoveFullWettingFrontDown(1)
                else: # es kommt nich genug nach um sie zu erhalten
                    newFullWettingFront = -1 # wetting front beendet
                    if currentSurfacePonding + previousTimeStepLeftover >= fieldCapacity1: # es ist genug um die field capacity zu füllen
                        layer1WaterDistribution[timeIndex][1] = previosSublayer0Leftover
                        layer1WaterDistribution[timeIndex][0] = currentSurfacePonding + previousTimeStepLeftover
                        LogSurfaceInteractions(currentSurfacePonding) # übergib die veränderung am surface ponding
                    else: # es ist nich genug da um die field capacity zu füllen
                        layer1WaterDistribution[timeIndex][1] = previosSublayer0Leftover - (fieldCapacity1 - currentSurfacePonding - previousTimeStepLeftover)
                        layer1WaterDistribution[timeIndex][0] = fieldCapacity1
                        LogSurfaceInteractions(currentSurfacePonding) # übergib die veränderung am surface ponding
            
            
            
            timeIndex = timeIndex + 1
        
        
        
        print("Simulation Finished")
        
        outputdata["Sublayer Storage Deviation"] = outputdata["Sum of Sublayer Storage"] - outputdata["Control Sum of Sublayer Storage"]
        
        UpdateMainPlot()
        
        ###########################################################################
        # detail plot neu bauen
        
        progressbar.step(progressbarStep)
        mainWindow.update()
        
        depthList = [] # zeigt die tiefe [mm] auf der y-achse an anstelle des sublayer counts
        for key in layer1WaterDistribution[1].keys():
            depthList.append(key * (sublayerThickness1))
        
        # convertiere x-achse in volumen prozente, damit gesamt wassermenge aus x*y abgeleitet werden kann
        layer1WaterDistributionPercent = pd.DataFrame.from_dict(layer1WaterDistribution) # in nem dataframe weil einfacher als in dict und genauso schnell
        layer1WaterDistributionPercent = layer1WaterDistributionPercent/0.15
        layer1WaterDistributionPercent = layer1WaterDistributionPercent.iloc[::-1] # umdrehen, damit wasser im graphen von oben nach unten fließt
        
        
        progressbar.step(progressbarStep)
        mainWindow.update()
        
        detailPlot.clf() # alles alte weg
        nonlocal detailWaterDistributionSubplot # bau den plott wieder auf
        detailWaterDistributionSubplot = detailPlot.add_subplot()
        nonlocal detailPlotLine
        detailPlotLine = detailWaterDistributionSubplot.plot(layer1WaterDistributionPercent[0], depthList, label = "Water Distribution")
        detailPlotLine = detailPlotLine[0] # aus irgendeinem grund wird das sonnst in eine liste mit nur einem eintrag gespeichert -> das holt es da raus und macht es dierekt in ein Lin2D object
        fieldCapacity1 = fieldCapacity1/sublayerThickness1
        detailWaterDistributionSubplot.add_line(plt.lines.Line2D([fieldCapacity1,fieldCapacity1],[thickness1,0], color="#888888", label="Field Capacity", linestyle = (0, (4, 4))))
        detailWaterDistributionSubplot.set_xlim(0, porosity1 *1.02) # zoomt die x achse auf 2% größer als der größte wert
        detailWaterDistributionSubplot.invert_yaxis()
        detailWaterDistributionSubplot.set(xlabel = "Water Amount [Volume/Volume]", ylabel = "Depth below Surface [mm]", title = "Water Distribution within Upper Layer at Minute 0")
        detailWaterDistributionSubplot.legend()
        
        detailPlotWidget.draw()
        
        
        detailIntensityPlot.clf() # alles alte weg
        detailIntensitySubplot = detailIntensityPlot.add_subplot()
        detailIntensitySubplot.plot(outputdata.index, outputdata["Intensity"], label = "Intensity")
        detailIntensitySubplot.set_xlim(0, len(layer1WaterDistribution))
        detailIntensitySubplot.set(ylabel = "[mm]")
        nonlocal detailIntensityLine # nen lila strich damit man sieht wo man zeitlich ist
        detailIntensityLine = plt.lines.Line2D([0, 0],[-10, outputdata["Intensity"].max() + 10], color="magenta")
        detailIntensitySubplot.add_line(detailIntensityLine)

        detailIntensityPlotWidget.draw()
        
        
        nonlocal detailPlotControler
        detailPlotControler.destroy() # controler auch weg 
        
        detailPlotControler = ttk.Scale(detailControlerFrame, from_=0, to=len(layer1WaterDistribution)-1, command=ScrollDetailPlot)
        detailPlotControler.pack(side="left", fill="x", padx=5, expand=True)
        
        
        progressbar.destroy()
    
    
    
    ###############################################################################
    # GUI und globale variablen
    
    
    # globale variablen
    outputdata = pd.DataFrame()
    layer1WaterDistribution = defaultdict(dict)
    layer1WaterDistributionPercent = pd.DataFrame()
    
    # fenster erstellen
    mainWindow = tkinter.Tk()
    mainWindow.state('zoomed')
    #mainWindow.geometry("1300x700")
    
    # fenster in rechte und linke hälfte unterteilen
    menueBar = ttk.Frame(mainWindow) # menüleiste
    menueBar.pack(side="left", fill="y", expand=False)
    menueTabs = ttk.Notebook(menueBar) # plot "Hülle" für tabs
    menueTabs.pack(side="left", fill="y", expand=False)
    plotArea = ttk.Frame(mainWindow)
    plotArea.pack(side="left", fill="both", expand=True)
    plotTabs = ttk.Notebook(plotArea) # plot "Hülle" für tabs
    plotTabs.pack(side="left", fill="both", expand=True)
    
    # eyecandy
    mainWindow.title("Infiltration- and runoffmodel")
    try: # icon eyecandy, in "try" damit nix kaput geht wenn das bild fehlt
        windowIcon = tkinter.PhotoImage(file = "icon.png")
        mainWindow.iconphoto(False, windowIcon)
        logo = ttk.Label(menueBar, image=windowIcon, padding=10)
        logo.image = windowIcon
        logo.place(rely=1, relx=0.5, anchor="s")
    except:
        print("Cant find Logo image.")
    
    
    
    ###############################################################################
    # plots erstellen
    
    
    
    # Summary
    mainPlotTab = ttk.Frame(plotTabs) # frame
    mainPlotTab.pack(side="top", fill="both", expand=True)
    plotTabs.add(mainPlotTab, text="Summary")
    
    mainPlot = plt.figure.Figure() # den canvas für den plot
    mainPlotWidget = FigureCanvasTkAgg(mainPlot, master=mainPlotTab) # den canvas in tkinter integrienren
    mainPlotWidget.get_tk_widget().pack(side="top", fill="both", expand=True)
    
    mainSubplot = mainPlot.add_subplot() # leerer plot damit das fenster am anfang nich leeer is
    mainSubplot.set(xlabel = "time [min]", ylabel = "Water Amount [mm]", title = "Summary")
    
    mainToolBarRestricor = ttk.Frame(mainPlotTab)
    mainToolBarRestricor.place(height=28, rely=1, anchor="sw")
    mainToolBar = NavigationToolbar2Tk(mainPlotWidget, mainToolBarRestricor, pack_toolbar=False)
    mainToolBar.pack(side="bottom")
    
    def UpdateMainPlot():
        mainPlot.clf() # lösche alles alte vom canvas
        mainSubplot = mainPlot.add_subplot() # mach nen neuen plot
        mainSubplot.set(xlabel = "time [min]", ylabel = "Water Amount [mm]", title = "Summary")
        try:
            if intensityActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Intensity"], label = "Intensity", color="blue")
            if surfacePondingActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Current Surface Ponding"], label = "Surface Ponding", color="green")
            if runoffActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Runoff"], label = "Runoff", color="#d6dd41")
            if surfaceInfiltrationActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Surface Infiltration"], label = "Surface Infiltration", color="#00cfff")
            if lowerInfiltrationActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Lower Layer Infiltration"], label = "Lower Layer Infiltration", color="#b968ff")
            if evaporationActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Evaporation"], label = "Evaporation")#, color="#b968ff")
            if sumOfSublayerActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Sum of Sublayer Storage"], label = "Sum of Sublayer Storage", color="#ff8800")
            if countedUpperLayerStorageActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Control Sum of Sublayer Storage"], label = "Control Sum of Sublayer Storage", color="black")
            if sublayerStorageDeviationActive.get():
                mainSubplot.plot(outputdata.index, outputdata["Sublayer Storage Deviation"], label = "Sublayer Storage Deviation", color="red")
            mainSubplot.legend()
        except:
            print("Error when plotting data.")
        mainPlotWidget.draw()
    
    
    # detail plot
    detailPlotTime = 0
    
    detailPlotTab = ttk.Frame(plotTabs) # frame
    detailPlotTab.pack(side="top", fill="both", expand=True)
    plotTabs.add(detailPlotTab, text="Water Distribution within Upper Layer")
    
    detailIntensityFrame = ttk.Frame(detailPlotTab)
    detailIntensityFrame.pack(side="top", fill="x")
    detailIntensityPlot = plt.figure.Figure(layout='constrained', figsize=(1, 100/plt.rcParams['figure.dpi']), ) # den canvas für den plot
    detailIntensityPlotWidget = FigureCanvasTkAgg(detailIntensityPlot, master=detailIntensityFrame) # den canvas in tkinter integrieren
    detailIntensityPlotWidget.get_tk_widget().pack(side="left", fill="x", expand=True)
    detailIntensityLine = plt.lines.Line2D((),(), color="magenta")
    detailIntensityLabelMin = tkinter.Label(detailIntensityFrame, text="time [min]", background="white", font=("Helvetica", 12))
    detailIntensityLabelMin.place(anchor="se", rely=0.9, relx=1)
    detailIntensitySubplot = detailIntensityPlot.add_subplot() # leerer plot damit das fenster am anfang nich leeer is und komisch aussieht
    detailIntensitySubplot.set(ylabel = "[mm]")    
    
    
    detailControlerFrame = ttk.Frame(detailPlotTab)
    detailControlerFrame.pack(side="top", fill="x")
    detailPlot = plt.figure.Figure(layout='constrained') # den canvas für den plot
    detailPlotWidget = FigureCanvasTkAgg(detailPlot, master=detailPlotTab) # den canvas in tkinter integrieren
    detailPlotWidget.get_tk_widget().pack(side="top", fill="both", expand=True)

    
    # initiale variablen damit beim ersten mal nix fehler prodoziert
    detailMinuteLabel = tkinter.Label(detailControlerFrame, text="Minute:", font=("Helvetica", 11, "bold"))
    detailMinuteLabel.pack(side="left", padx=5)
    detailPlotControler = ttk.Scale(detailControlerFrame) # initiate dummy widged damit es beim ersten ploten gelöscht werden kann
    detailPlotControler.pack(side="left", fill="x", padx=5, expand=True)
    detailPlotLine = plt.lines.Line2D((),()) # das ist die variable die überschrieben wird wenn der slider bewegt wird -> ist schneller als löschen und neu plotten
    detailWaterDistributionSubplot = detailPlot.add_subplot() # leerer plot damit das fenster am anfang nich leeer is und komisch aussieht
    detailWaterDistributionSubplot.set(xlabel = "Water Amount [Volume/Volume]", ylabel = "Depth below Surface [mm]", title = "Water Distribution within Upper Layer at Minute 0")
    
    
    def ScrollDetailPlot(timeIndex):
        timeIndex = float(timeIndex) # die werte kommen als string -> muss int draus machen
        timeIndex = int(timeIndex)
        detailPlotLine.set_xdata([layer1WaterDistributionPercent[timeIndex]])
        detailWaterDistributionSubplot.set_title("Water Distribution within Upper Layer at Minute " + str(timeIndex))
        detailPlotWidget.draw()
        detailIntensityLine.set_xdata([timeIndex, timeIndex])
        detailIntensityPlotWidget.draw()
        nonlocal detailPlotTime
        detailPlotTime = timeIndex
    
    
    detailToolBarRestricor = ttk.Frame(detailPlotTab)
    detailToolBarRestricor.place(height=28, rely=1, anchor="sw")
    detailToolBar = NavigationToolbar2Tk(detailPlotWidget, detailToolBarRestricor, pack_toolbar=False)
    detailToolBar.pack(side="bottom")
    
    
    # File sektion in plotArea erstellen
    fileFrame = ttk.Frame(plotArea)
    fileFrame.place(rely=0, relx=1, anchor="ne")
    filePathBox = ttk.Entry(fileFrame, width=40)
    filePathBox.pack(side="right", padx=10)
    filePathBox.insert(0, "No File Selected")
    filePathLabel = ttk.Label(fileFrame, text = "Path to CSV File:")
    filePathLabel.pack(side="right")
    
    
    
    ###############################################################################
    # input erstellen 
    
    
    inputMenueTab = ttk.Frame(menueTabs) # frame
    inputMenueTab.pack(side="left", fill="y", expand=False)
    menueTabs.add(inputMenueTab, text="Input")
    
        # File sektion in inputMenueTab erstellen
    inputFileFrame = ttk.LabelFrame(inputMenueTab, text="Input File", borderwidth=5)
    inputFileFrame.pack(side="top", padx=5, pady=5, fill="x")
    inpuFileButtonFrame = ttk.Frame(inputFileFrame)
    inpuFileButtonFrame.pack(side="top", pady=5, fill="x")
    def ChooseInputFile():
        inputFilePath = tkinter.filedialog.askopenfilename(initialdir = "/", title = "Select Input CSV File", filetypes = (("csv files","*.CSV"), ("all files","*.*")))
        filePathBox.delete(0,'end')
        filePathBox.insert(0, inputFilePath)
        print (inputFilePath)
    inputSelectButton = ttk.Button(inpuFileButtonFrame, text="Choose CSV", command=ChooseInputFile)
    inputSelectButton.pack(side="left")
    
        # eineheiten hilfe fenster
    def InputUnitFactorExplainer():
        inputPopup = tkinter.Toplevel(mainWindow)
        inputPopup.title("Information")
        inputPopupLabel = ttk.Label(inputPopup, text= 'This model assumes rain intensity data in [mm/min]. Any data that is not resolved in minutes might lead to unpredictable behaviour. If your CSV file has a different unit then millimeter resolved per minute, you can enter a factor in "Unit Correction Factor" to convert your data into [mm/min]. EXAMPLE: Your CSV data is in [inch/min], so 25.4 is entered as a correction factor to archive [mm/min].', wraplength=300)
        inputPopupLabel.pack(padx=30, pady=30)
    inputUnitFactorExplainer = ttk.Button(inpuFileButtonFrame, text="Help with Units", command=InputUnitFactorExplainer)
    inputUnitFactorExplainer.pack(side="right")
    
        # welcher seperator ist in der datei
    inputSeperatorFrame = ttk.Frame(inputFileFrame)
    inputSeperatorFrame.pack(side="top", pady=5, fill="x")
    inputSeperatorLabel = ttk.Label(inputSeperatorFrame, text="Value Seperator")
    inputSeperatorLabel.pack(side="left")
    inputSeperatorBox = ttk.Entry(inputSeperatorFrame, width=8)
    inputSeperatorBox.insert(0, ",")
    inputSeperatorBox.pack(side="right")
        # relevante spalte
    inputColumnFrame = ttk.Frame(inputFileFrame)
    inputColumnFrame.pack(side="top", pady=5, fill="x")
    inputColumnNameLabel = ttk.Label(inputColumnFrame, text="Column with [intensity/min] Data")#, wraplength=110)
    inputColumnNameLabel.pack(side="top", fill="x")
    inputColumnNameBox = ttk.Entry(inputColumnFrame, width=30)
    inputColumnNameBox.pack(side="top", fill="x")
        # einheitenkorrektur
    inputUnitFactorFrame = ttk.Frame(inputFileFrame)
    inputUnitFactorFrame.pack(side="top", pady=5, fill="x")
    inputUnitFactorLabel = ttk.Label(inputUnitFactorFrame, text="Unit Correction Factor")#, wraplength=110)
    inputUnitFactorLabel.pack(side="top", fill="x")
    inputUnitFactorBox = ttk.Entry(inputUnitFactorFrame, width=8)
    inputUnitFactorBox.insert(0, 1)
    inputUnitFactorBox.place(anchor="ne", relx=1, rely=0)
    
    # parameter input für layer 1
    inputLayer1Frame = ttk.LabelFrame(inputMenueTab, text="Surface Layer Parameters", borderwidth=5)
    inputLayer1Frame.pack(side="top", padx=5, pady=5, fill="x")
    
    inputLayer1ThicknessFrame = ttk.Frame(inputLayer1Frame)
    inputLayer1ThicknessFrame.pack(side="top", pady=5, fill="x")
    inputLayer1ThicknessLabel = ttk.Label(inputLayer1ThicknessFrame, text= "Thickness [mm]")
    inputLayer1ThicknessLabel.pack(side="left")
    inputLayer1ThicknessBox = ttk.Entry(inputLayer1ThicknessFrame, width=8)
    inputLayer1ThicknessBox.pack(side="right")
    
    inputLayer1HydraulicConFrame = ttk.Frame(inputLayer1Frame)
    inputLayer1HydraulicConFrame.pack(side="top", pady=5, fill="x")
    inputLayer1HydraulicConLabel = ttk.Label(inputLayer1HydraulicConFrame, text= "Hydraulic Conductivity [mm/min]", wraplength=140)
    inputLayer1HydraulicConLabel.pack(side="left")
    inputLayer1HydraulicConBox = ttk.Entry(inputLayer1HydraulicConFrame, width=8)
    inputLayer1HydraulicConBox.pack(side="right")
    
    inputLayer1PorosityFrame = ttk.Frame(inputLayer1Frame)
    inputLayer1PorosityFrame.pack(side="top", pady=5, fill="x")
    inputLayer1PorosityLabel = ttk.Label(inputLayer1PorosityFrame, text= "Porosity [Volume/Volume]")
    inputLayer1PorosityLabel.pack(side="left")
    inputLayer1PorosityBox = ttk.Entry(inputLayer1PorosityFrame, width=8)
    inputLayer1PorosityBox.pack(side="right")
    
    inputLayer1InitialH2OFrame = ttk.Frame(inputLayer1Frame)
    inputLayer1InitialH2OFrame.pack(side="top", pady=5, fill="x")
    inputLayer1InitialH2OLabel = ttk.Label(inputLayer1InitialH2OFrame, text= "Initial Water Content [Volume/Volume]", wraplength=140)
    inputLayer1InitialH2OLabel.pack(side="left")
    inputLayer1InitialH2OBox = ttk.Entry(inputLayer1InitialH2OFrame, width=8)
    inputLayer1InitialH2OBox.pack(side="right")
    
    inputLayer1FieldKapacityFrame = ttk.Frame(inputLayer1Frame)
    inputLayer1FieldKapacityFrame.pack(side="top", pady=5, fill="x")
    inputLayer1FieldKapacityLabel = ttk.Label(inputLayer1FieldKapacityFrame, text= "Field Capacity [Volume/Volume]", wraplength=140)
    inputLayer1FieldKapacityLabel.pack(side="left")
    inputLayer1FieldKapacityBox = ttk.Entry(inputLayer1FieldKapacityFrame, width=8)
    inputLayer1FieldKapacityBox.pack(side="right")
    
    
    # parameter input für Model Boundary
    inputlayer2Frame = ttk.LabelFrame(inputMenueTab, text="Model Boundary Parameters", borderwidth=5)
    inputlayer2Frame.pack(side="top", padx=5, pady=5, fill="x")
    
    inputMaxPondingFrame = ttk.Frame(inputlayer2Frame)
    inputMaxPondingFrame.pack(side="top", pady=5, fill="x")
    inputMaxPondingLabel = ttk.Label(inputMaxPondingFrame, text= "Max. Surface Ponding [mm]", wraplength=140)
    inputMaxPondingLabel.pack(side="left")
    inputMaxPondingBox = ttk.Entry(inputMaxPondingFrame, width=8)
    inputMaxPondingBox.pack(side="right")
    
    inputlayer2HydraulicConFrame = ttk.Frame(inputlayer2Frame)
    inputlayer2HydraulicConFrame.pack(side="top", pady=5, fill="x")
    inputlayer2HydraulicConLabel = ttk.Label(inputlayer2HydraulicConFrame, text= "Hydraulic Conductivity of Lower Layer [mm/min]", wraplength=140)
    inputlayer2HydraulicConLabel.pack(side="left")
    inputlayer2HydraulicConBox = ttk.Entry(inputlayer2HydraulicConFrame, width=8)
    inputlayer2HydraulicConBox.pack(side="right")
    
    inputEvaporationFrame = ttk.Frame(inputlayer2Frame)
    inputEvaporationFrame.pack(side="top", pady=5, fill="x")
    inputEvaporationLabel = ttk.Label(inputEvaporationFrame, text= "Mean Evaporation [mm/min]", wraplength=140)
    inputEvaporationLabel.pack(side="left")
    inputEvaporationBox = ttk.Entry(inputEvaporationFrame, width=8)
    inputEvaporationBox.pack(side="right")
    

    
    
    # start und export bvutton und funktionen
    startButton = ttk.Button(inputMenueTab, text="Start Simulation", command=RunSimulation)
    startButton.pack(side="top", padx=10, pady=5)
    
    def ExportSumaryData():
        file = tkinter.filedialog.asksaveasfile(initialdir = "/", title = "Save Sumary Data as CSV File", defaultextension=".csv", filetypes = (("csv files","*.CSV"), ("all files","*.*")))
        if file:
            outputdata.to_csv(file)
            file.close()
    inputSelectButton = ttk.Button(inputMenueTab, text="Export Sumary Data", command=ExportSumaryData)
    inputSelectButton.pack(side="top", padx=10, pady=5)
    
    def ExportUperLayerData():
        file = tkinter.filedialog.asksaveasfile(initialdir = "/", title = "Save Sublayer Data [Volume/Volume] as CSV File", defaultextension=".csv", filetypes = (("csv files","*.CSV"), ("all files","*.*")))
        if file:
            layer1WaterDistributionPercent.iloc[::-1].transpose().to_csv(file) # umdrehen damit das obere sublayer oben ist und sublayer - spaltren, zeit - zeilen
            file.close()
    inputSelectButton = ttk.Button(inputMenueTab, text="Export Sublayer Data [Volume/Volume]", command=ExportUperLayerData)
    inputSelectButton.pack(side="top", padx=10, pady=5)
    
    
    
    #######################################################################################
    # Plot control tab
    
    
    plotControlTab = ttk.Frame(menueTabs, padding=10) # frame
    plotControlTab.pack(side="left", fill="y", expand=False)
    menueTabs.add(plotControlTab, text="Plot Settings")    
    
    modelBoundariesFrame = ttk.LabelFrame(plotControlTab, text="Model Boundaries", borderwidth=5)
    modelBoundariesFrame.pack(side="top", padx=5, pady=5, fill="x")
    
    intensityActive = tkinter.BooleanVar()
    intensityActive.set(True)
    intensityCheckBox = ttk.Checkbutton(modelBoundariesFrame, text = "Intensity", variable=intensityActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    intensityCheckBox.pack(side="top", pady=5, fill="x")
    
    lowerInfiltrationActive = tkinter.BooleanVar()
    lowerInfiltrationActive.set(True)
    lowerInfiltrationCheckBox = ttk.Checkbutton(modelBoundariesFrame, text = "Lower Layer Infiltration", variable=lowerInfiltrationActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    lowerInfiltrationCheckBox.pack(side="top", pady=5, fill="x")
    
    surfaceInteractionFrame = ttk.LabelFrame(plotControlTab, text="Surface Interaction", borderwidth=5)
    surfaceInteractionFrame.pack(side="top", padx=5, pady=5, fill="x")
    
    surfaceInfiltrationActive = tkinter.BooleanVar()
    surfaceInfiltrationActive.set(True)
    surfaceInfiltrationCheckBox = ttk.Checkbutton(surfaceInteractionFrame, text = "Surface Infiltration", variable=surfaceInfiltrationActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    surfaceInfiltrationCheckBox.pack(side="top", pady=5, fill="x")
    
    surfacePondingActive = tkinter.BooleanVar()
    surfacePondingActive.set(True)
    surfacePondingCheckBox = ttk.Checkbutton(surfaceInteractionFrame, text = "Surface Ponding", variable=surfacePondingActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    surfacePondingCheckBox.pack(side="top", pady=5, fill="x")
    
    runoffActive = tkinter.BooleanVar()
    runoffActive.set(True)
    runoffCheckBox = ttk.Checkbutton(surfaceInteractionFrame, text = "Runoff", variable=runoffActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    runoffCheckBox.pack(side="top", pady=5, fill="x")
    
    evaporationActive = tkinter.BooleanVar()
    evaporationActive.set(True)
    evaporationCheckBox = ttk.Checkbutton(surfaceInteractionFrame, text = "Evaporation", variable=evaporationActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    evaporationCheckBox.pack(side="top", pady=5, fill="x")
    
    
    upperLayerDataFrame = ttk.LabelFrame(plotControlTab, text="Upper Layer Data", borderwidth=5)
    upperLayerDataFrame.pack(side="top", padx=5, pady=5, fill="x")
    
    sumOfSublayerActive = tkinter.BooleanVar()
    sumOfSublayerActive.set(True)
    sumOfSublayerCheckBox = ttk.Checkbutton(upperLayerDataFrame, text = "Sum of Sublayer Storage", variable=sumOfSublayerActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    sumOfSublayerCheckBox.pack(side="top", pady=5, fill="x")
    
    countedUpperLayerStorageActive = tkinter.BooleanVar()
    countedUpperLayerStorageActive.set(True)
    countedUpperLayerStorageCheckBox = ttk.Checkbutton(upperLayerDataFrame, text = "Control Sum of Sublayer Storage", variable=countedUpperLayerStorageActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    countedUpperLayerStorageCheckBox.pack(side="top", pady=5, fill="x")
    
    sublayerStorageDeviationActive = tkinter.BooleanVar()
    sublayerStorageDeviationActive.set(True)
    sublayerStorageDeviationCheckBox = ttk.Checkbutton(upperLayerDataFrame, text = "Sublayer Storage Deviation", variable=sublayerStorageDeviationActive, command=UpdateMainPlot, offvalue=False, onvalue=True)
    sublayerStorageDeviationCheckBox.pack(side="top", pady=5, fill="x")
    
    
    
    
    # values for quick debungging
    def DebugValues():
        filePathBox.delete(0,'end')
        filePathBox.insert(0, r"D:\I_R_Model\fictional_test_data_2.csv")
        inputSeperatorBox.delete(0,'end')
        inputSeperatorBox.insert(0, ";")
        inputColumnNameBox.delete(0,'end')
        inputColumnNameBox.insert(0, "Intensität")
        
        inputLayer1ThicknessBox.insert(0, 40)
        inputLayer1HydraulicConBox.insert(0, 0.06)
        inputLayer1PorosityBox.insert(0, 0.4)
        inputLayer1InitialH2OBox.insert(0, 0.05)
        inputLayer1FieldKapacityBox.insert(0, 0.1)
        
        inputMaxPondingBox.insert(0, 0.4)
        inputlayer2HydraulicConBox.insert(0, 0.01)
        inputEvaporationBox.insert(0, 0.001)
        
        mainWindow.update()
        
        RunSimulation()
        
    DebugValues()
    
    
    
    
    # Updaten
    mainWindow.mainloop()
    
InflitrationModel()
