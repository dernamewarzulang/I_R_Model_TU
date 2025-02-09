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
        
        # progressbar so we can see that something is happening
        nonlocal mainWindow
        progressbar = ttk.Progressbar(mainWindow)
        progressbar.place(anchor="sw", relwidth=1, relx=0, rely=1)
        progressbar.step(0)
        progressbarCurrentState = 0
        mainWindow.update()
        
        # reset all databases so there are no errors wher running multiple times without closing the GUI in between
        nonlocal outputdata
        outputdata = pd.DataFrame()
        nonlocal layer1WaterDistribution
        layer1WaterDistribution = defaultdict(dict)
        nonlocal layer1WaterDistributionPercent
        layer1WaterDistributionPercent = pd.DataFrame()
        
        
        # read the unit correction factor 
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
        
        
        try: # read the parameters for the upper layer
            thickness1 = float(inputLayer1ThicknessBox.get()) # storage of the upper layer is Tickness [mm] * Porosity
            hydraulicCon1 = float(inputLayer1HydraulicConBox.get()) # [mm/min]
            porosity1 = float(inputLayer1PorosityBox.get())   # [Vol/Vol]
            initialWatercontent1 = float(inputLayer1InitialH2OBox.get()) # [Vol/Vol]
            fieldCapacity1 = float(inputLayer1FieldKapacityBox.get()) # [Vol/Vol]
            if initialWatercontent1 > porosity1 or fieldCapacity1 > porosity1: # make shure we dont have conflicting parameters
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
        
        try: # parameters for the lower model boundary
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
        # read input CSV and prepare the output databank
        
        # read file with given seperator
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
        
        # create colums in the output dataframe
        try:
            outputdata["Intensity"] = inputdata[inputColumnName] * inputUnitFactor  # this is the reason for the "try:", the other columns are just in here to keap a better overwiew of the existing columns
            outputdata["Surface Infiltration"] = ""
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
        
        outputdata.index = outputdata.index + 1 # move all indecese so we can provide a starting point in the database of the sublayers that is at time 0. otherwhise we would have to do special cases for the data access just for the first itteration.
        
        
        ###############################################################################
        # define functions used in simulation
        
        
        def LogSurfaceInteractions(currentSurfaceInfiltration): # handels runnoff and saving data to output data frame
            
            nonlocal currentLayer1Storage
            currentLayer1Storage = currentLayer1Storage + currentSurfaceInfiltration
            nonlocal currentSurfacePonding
            currentSurfacePonding = currentSurfacePonding - currentSurfaceInfiltration
            
            nonlocal runOff
            if currentSurfacePonding > maxSufacePonding: # calculate runoff
                runOff = currentSurfacePonding - maxSufacePonding
                currentSurfacePonding = maxSufacePonding
            else:
                runOff = 0
                
            # save all produced data to the output dataframe - this is happening in one call because it will hapen every simulated minute and would otherwhise slow down the simlation by handeling too many dataframe access calls.
            outputdata.loc[timeIndex] = [outputdata.at[timeIndex,"Intensity"], currentSurfaceInfiltration, runOff, currentSurfacePonding, currentLowerLayerInfiltration, currentEvaporation, currentLayer1Storage, sum(layer1WaterDistribution[timeIndex].values())]
                
            
            
        def MoveFullWettingFrontDown(newFullWettingFrontPosition): # this allows the marker for the wettingfront to move down all the way to the last fully filles sublayer. this helps when a wetting front "catches" a slower pocket of water and combines with it.
            nonlocal newFullWettingFront
            while layer1WaterDistribution[timeIndex][newFullWettingFrontPosition] >= hydraulicCon1:
                newFullWettingFront = newFullWettingFrontPosition
                newFullWettingFrontPosition = newFullWettingFrontPosition+1
        
        
        ###############################################################################
        # calculate initial values and instantiate variables to avoid instantiating them in every loop itteration
        
        
        sublayerThickness1 = hydraulicCon1/porosity1
        sublayerCount1 = round(thickness1 / (sublayerThickness1)) # set the sublayer thickness so that the contained water can always move one sublayer every itteration (=haydraulic conductivity in [mm/min])
        if sublayerCount1 < 3: # make shure we have enough sublayers to not runn into issues
            inputPopup = tkinter.Toplevel(mainWindow)
            inputPopup.title("ERROR")
            inputPopupLabel = ttk.Label(inputPopup, text= 'ERROR: The amount of sublayer resulting from the current inputs for the upper layer is below 3. This tool requires at least 3 Sublayers. The thickness of the sublayers is calculated as the distance water can travel within the soil over one minute by [Hydraulic Conductivity / Porosity]. The amount of sublayers then results from [Thickness of the upper layer / Thickness of the sublayers].', wraplength=360)
            inputPopupLabel.pack(padx=30, pady=30)
            progressbar.destroy()
            return
        
        initialSublayerWatercontent1 = (sublayerThickness1) * initialWatercontent1 # convert Vol/Vol (volume fraction) into mm water per sublayer
        fieldCapacity1 = (sublayerThickness1) * fieldCapacity1  # convert Vol/Vol (volume fraction) into mm water per sublayer
        
        # database for the sublayers. this is not a dataframe because it prooved to be very slow when accessing it many times per simluated minute per sublayer. dictionarys are way faster and "default dict" handles atomatic creation of missing keys.
        layer1WaterDistribution[0] = dict.fromkeys(range(sublayerCount1), initialSublayerWatercontent1)
        
        ### initial values
        timeIndex = 1
        currentSurfacePonding = 0
        previousTimeStepLeftover = 0
        waterToBeMoved = 0
        newFullWettingFront = -1 # a satturated wetting front that is still being "fed" from the top has the ability "push" water held in the field capacity in front of itself. this is important, because otherwhise the maximum infiltration will be hydraulic conductivity - fieldcapacity and never reach the intended maximum of hydraulic conductivity. 
        currentLayer1Storage = thickness1 * initialWatercontent1 # this is the control value for the sum of all sublayer storage to spot errors
        currentLowerLayerInfiltration = 0
        runOff = 0
        currentEvaporation = 0
        previosSublayer0Leftover = initialSublayerWatercontent1
        progressbarStep = round(len(inputdata.index)*0.05)
        
        
        ####################################################################################
        ### simulation Loop for every minute
        
        
        print("Starting Simulation")
        for inputIntensity in outputdata["Intensity"]:
            
            if timeIndex == progressbarCurrentState + progressbarStep: # mainwindow.update() is very slow so it is faster to compare evry time and just update every 5% of progress
                progressbar.step(progressbarStep)
                progressbarCurrentState = progressbarCurrentState + progressbarStep
                mainWindow.update()
                
                
            ####################################################################################
            ### how much water infiltrates from the lowest sublayer into the lower soil layer?
            
            
            if layer1WaterDistribution[timeIndex-1][sublayerCount1-1] <= fieldCapacity1: # if water is below field capcity do nothing
                previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][sublayerCount1-1]
                currentLowerLayerInfiltration = 0
            elif layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - fieldCapacity1 < HydraulicConacity2: # if potential infiltration is lower then the maximum (Hydraulic Conductivity 2)
                previousTimeStepLeftover = fieldCapacity1
                currentLowerLayerInfiltration = layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - fieldCapacity1
                currentLayer1Storage = currentLayer1Storage - (layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - fieldCapacity1)
            else: # if potential infiltration is larger then the maximum (Hydraulic Conductivity 2)
                previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][sublayerCount1-1] - HydraulicConacity2
                currentLowerLayerInfiltration = HydraulicConacity2
                currentLayer1Storage = currentLayer1Storage - HydraulicConacity2
           
            
            ####################################################################################
            # itterate through all sublayers in between the lowest and the two highest
            
            
            for subLayerIndex in reversed(range(2, sublayerCount1)): # reversed range so that we itterate from lowest to highest (otherwhise we get a wave like behavior as water from a sublayer tries to infiltrate into one bwlo it, without the one below having the chance to "give away" its own water even further down)
                
                if newFullWettingFront >= subLayerIndex-2: # if a new wetting front is lower or at two layers above us
                    waterToBeMoved = layer1WaterDistribution[timeIndex-1][subLayerIndex-1]
                    if previousTimeStepLeftover + waterToBeMoved >= hydraulicCon1: # if we cant take all the water because we are already quite full
                        layer1WaterDistribution[timeIndex][subLayerIndex] = hydraulicCon1
                        previousTimeStepLeftover = waterToBeMoved - (hydraulicCon1 - previousTimeStepLeftover)
                        if newFullWettingFront == subLayerIndex-2 or newFullWettingFront == subLayerIndex-1: # if it was just above us, move the wetting front down
                            MoveFullWettingFrontDown(subLayerIndex)
                    else: # if all the water fits into our sublayer and is less then the maximum
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover + waterToBeMoved
                        previousTimeStepLeftover = 0
                        
                elif layer1WaterDistribution[timeIndex-1][subLayerIndex-1] > fieldCapacity1: # when the sublayer above us has more water then can be held by gravity (field capacity)
                    waterToBeMoved = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] - fieldCapacity1
                    if previousTimeStepLeftover + waterToBeMoved > hydraulicCon1: # if we cant take all the water because we are already quite full
                        layer1WaterDistribution[timeIndex][subLayerIndex] = hydraulicCon1
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] - (hydraulicCon1 - previousTimeStepLeftover)
                    else: # if all the water fits into our sublayer and is less then the maximum
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover + waterToBeMoved
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] - waterToBeMoved
                else: # if the sublayer above us can hold all its water against gravity
                    if previousTimeStepLeftover >= fieldCapacity1: # when our sublayer has more water then we can hold against gravity
                        waterToBeMoved = (fieldCapacity1 - layer1WaterDistribution[timeIndex-1][subLayerIndex-1]) / 2
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover - waterToBeMoved
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] + waterToBeMoved
                    else: # if our sublayer can also hold all its water against gravity
                        waterToBeMoved = (previousTimeStepLeftover - layer1WaterDistribution[timeIndex-1][subLayerIndex-1]) / 2
                        layer1WaterDistribution[timeIndex][subLayerIndex] = previousTimeStepLeftover - waterToBeMoved
                        previousTimeStepLeftover = layer1WaterDistribution[timeIndex-1][subLayerIndex-1] + waterToBeMoved
                        
                        
            ####################################################################################
            # 1. and 2. sublayer + infiltration + evaporation + starting/maintaining/ending wetting fronts
            
            
            currentSurfacePonding = currentSurfacePonding + inputIntensity # how much water is on the surface this minute
            if currentSurfacePonding >= evaporation: # when there is enough ponded to cover evaporation
                currentSurfacePonding = currentSurfacePonding - evaporation
                currentEvaporation = evaporation
                previosSublayer0Leftover = layer1WaterDistribution[timeIndex-1][0]
            elif layer1WaterDistribution[timeIndex-1][0] + currentSurfacePonding > evaporation: # when some evaporation has to hapen from the first sublayer, but its enough for maximum evaporation
                previosSublayer0Leftover = layer1WaterDistribution[timeIndex-1][0] - (evaporation - currentSurfacePonding)
                currentLayer1Storage = currentLayer1Storage - (evaporation - currentSurfacePonding)
                currentSurfacePonding = 0
                currentEvaporation = evaporation
            else: # if there is less water then could evaporate ponded + 1. sublayer
                currentEvaporation = layer1WaterDistribution[timeIndex-1][0] + currentSurfacePonding
                currentLayer1Storage = currentLayer1Storage - layer1WaterDistribution[timeIndex-1][0]
                currentSurfacePonding = 0
                previosSublayer0Leftover = 0
            
            
            
            
            if newFullWettingFront == -1: # if we dont have a wetting front right now
                # calculate the hypothetical water movement between the two upper layer
                if previosSublayer0Leftover > fieldCapacity1:  # when the 1. sublayer has more water then can be held by gravity (field capacity)
                    waterToBeMoved = previosSublayer0Leftover - fieldCapacity1
                    if previousTimeStepLeftover + waterToBeMoved >= hydraulicCon1: # if the 2. sublayer cant take all the water because we are already quite full
                        waterToBeMoved = waterToBeMoved - (previousTimeStepLeftover + waterToBeMoved - hydraulicCon1)                    
                elif previousTimeStepLeftover >= fieldCapacity1: # if the 1. sublayer can hold all its water against gravity and the 2. cant
                    waterToBeMoved = (previosSublayer0Leftover - fieldCapacity1) / 2
                else: # if the 2. sublayer can also hold all its water against gravity
                    waterToBeMoved = (previosSublayer0Leftover - previousTimeStepLeftover) / 2
                
                # do we get a new weting front?
                if currentSurfacePonding + previosSublayer0Leftover - waterToBeMoved >= hydraulicCon1: # yes: we expect the 1. sublayer to fill to capactiyt (taking into account the hypothetical water movement calculated)
                    if currentSurfacePonding + previosSublayer0Leftover <= hydraulicCon1: # if water raising from the 2. sublayer is causing the first to reach capacity
                        layer1WaterDistribution[timeIndex][1] = previousTimeStepLeftover
                        layer1WaterDistribution[timeIndex][0] = currentSurfacePonding + previosSublayer0Leftover
                        LogSurfaceInteractions(currentSurfacePonding) # save values in output dataframe and calculate runoff
                    else:
                        if currentSurfacePonding >= hydraulicCon1: # if the surfcae water available exceeds infiltration capacity
                            waterToBeMoved = previosSublayer0Leftover
                        else: # if the surface water available is less then the infiltration capacity
                            waterToBeMoved = previosSublayer0Leftover - (hydraulicCon1 - currentSurfacePonding) #  how much water we would need to transfer from the 1. to the 2. sublayer to not exceed capacity in the 1.
                        if previousTimeStepLeftover + waterToBeMoved < hydraulicCon1: # if everything that can move from the 1. sublayer into the 2. can do so
                            layer1WaterDistribution[timeIndex][1] = previousTimeStepLeftover + waterToBeMoved
                            layer1WaterDistribution[timeIndex][0] = hydraulicCon1
                            newFullWettingFront = 0
                            if currentSurfacePonding >= hydraulicCon1:
                                LogSurfaceInteractions(hydraulicCon1) # save values in output dataframe and calculate runoff
                            else:
                                LogSurfaceInteractions(currentSurfacePonding) # save values in output dataframe and calculate runoff
                        else: # if the 2. sublayer would exceed capacity with the water from the 1.
                            layer1WaterDistribution[timeIndex][1] = hydraulicCon1
                            layer1WaterDistribution[timeIndex][0] = hydraulicCon1
                            MoveFullWettingFrontDown(1)
                            LogSurfaceInteractions(hydraulicCon1 - previosSublayer0Leftover + (hydraulicCon1 - previousTimeStepLeftover)) # save values in output dataframe and calculate runoff
                else: # no: the 1. sublayer will not exceed capacity, everything can infiltrate
                    layer1WaterDistribution[timeIndex][1] = previousTimeStepLeftover + waterToBeMoved
                    layer1WaterDistribution[timeIndex][0] = previosSublayer0Leftover - waterToBeMoved + currentSurfacePonding
                    LogSurfaceInteractions(currentSurfacePonding) # save values in output dataframe and calculate runoff
            elif newFullWettingFront >= 0: # if we already have a wetting front
                if currentSurfacePonding + previousTimeStepLeftover >= hydraulicCon1: # if there is enough water on the surface to sustain the wetting front
                    layer1WaterDistribution[timeIndex][1] = hydraulicCon1
                    layer1WaterDistribution[timeIndex][0] = hydraulicCon1
                    LogSurfaceInteractions(hydraulicCon1 - previousTimeStepLeftover) # save values in output dataframe and calculate runoff
                    if newFullWettingFront == 0 or newFullWettingFront == 1: # if it was in the 1. or 2. sublayer, move the wetting front down
                        MoveFullWettingFrontDown(1)
                else: # there is not enough water on the surface to sustain the wetting front
                    newFullWettingFront = -1 # stop the wetting front
                    if currentSurfacePonding + previousTimeStepLeftover >= fieldCapacity1: # there is enough water to fille the field capacity in the 1. sublayer
                        layer1WaterDistribution[timeIndex][1] = previosSublayer0Leftover
                        layer1WaterDistribution[timeIndex][0] = currentSurfacePonding + previousTimeStepLeftover
                        LogSurfaceInteractions(currentSurfacePonding) # save values in output dataframe and calculate runoff
                    else: # there is too little water to fill the field capacity in the 1. sublayer
                        layer1WaterDistribution[timeIndex][1] = previosSublayer0Leftover - (fieldCapacity1 - currentSurfacePonding - previousTimeStepLeftover)
                        layer1WaterDistribution[timeIndex][0] = fieldCapacity1
                        LogSurfaceInteractions(currentSurfacePonding) # save values in output dataframe and calculate runoff
            
            
            
            timeIndex = timeIndex + 1
        
        
        
        print("Simulation Finished")
        
        outputdata["Sublayer Storage Deviation"] = outputdata["Sum of Sublayer Storage"] - outputdata["Control Sum of Sublayer Storage"]
        
        UpdateMainPlot()
        
        ###########################################################################
        # construct the detail plot
        
        progressbar.step(progressbarStep)
        mainWindow.update()
        
        depthList = [] # needed to have [mm] dpeth on the y-achses and not the sublayer count
        for key in layer1WaterDistribution[1].keys():
            depthList.append(key * (sublayerThickness1))
        
        # convert x-achses in volume/volume, so that the total amount of water in mm can be derived from x*y
        layer1WaterDistributionPercent = pd.DataFrame.from_dict(layer1WaterDistribution) # convert to dataframe for easy handeling
        layer1WaterDistributionPercent = layer1WaterDistributionPercent/0.15
        layer1WaterDistributionPercent = layer1WaterDistributionPercent.iloc[::-1] # invert order so the water flows down in the graph and not up
        
        
        progressbar.step(progressbarStep)
        mainWindow.update()
        
        # the deatiled location of the water in the upper layer
        detailPlot.clf() # clear all old plot elements to prevent bugs when displaying new ones
        nonlocal detailWaterDistributionSubplot
        detailWaterDistributionSubplot = detailPlot.add_subplot()
        nonlocal detailPlotLine
        detailPlotLine = detailWaterDistributionSubplot.plot(layer1WaterDistributionPercent[0], depthList, label = "Water Distribution")
        detailPlotLine = detailPlotLine[0] # for some reason this variable is saved in a list with a singlke entry -> this line removes the list part and makes it a Lin2D object
        fieldCapacity1 = fieldCapacity1/sublayerThickness1
        detailWaterDistributionSubplot.add_line(plt.lines.Line2D([fieldCapacity1,fieldCapacity1],[thickness1,0], color="#888888", label="Field Capacity", linestyle = (0, (4, 4))))
        detailWaterDistributionSubplot.set_xlim(0, porosity1 *1.02) # zoomt the x-achses to 2% larger then the largest value -> this prevents rezising of the plot for each new minute displayed
        detailWaterDistributionSubplot.invert_yaxis()
        detailWaterDistributionSubplot.set(xlabel = "Water Amount [Volume/Volume]", ylabel = "Depth below Surface [mm]", title = "Water Distribution within Upper Layer at Minute 0")
        detailWaterDistributionSubplot.legend()
        
        detailPlotWidget.draw()
        
        # a helper graph to see where the current time displayed is
        detailIntensityPlot.clf() # clear all old plot elements to prevent bugs when displaying new ones
        detailIntensitySubplot = detailIntensityPlot.add_subplot()
        detailIntensitySubplot.plot(outputdata.index, outputdata["Intensity"], label = "Intensity")
        detailIntensitySubplot.set_xlim(0, len(layer1WaterDistribution))
        detailIntensitySubplot.set(ylabel = "[mm]")
        nonlocal detailIntensityLine # a purple line to show which time is selected
        detailIntensityLine = plt.lines.Line2D([0, 0],[-10, outputdata["Intensity"].max() + 10], color="magenta")
        detailIntensitySubplot.add_line(detailIntensityLine)

        detailIntensityPlotWidget.draw()
        
        
        nonlocal detailPlotControler
        detailPlotControler.destroy() # redo the controler bar to fit any changes in length of simulation 
        
        detailPlotControler = ttk.Scale(detailControlerFrame, from_=0, to=len(layer1WaterDistribution)-1, command=ScrollDetailPlot)
        detailPlotControler.pack(side="left", fill="x", padx=5, expand=True)
        
        
        progressbar.destroy() # clear the progressbar
    
    
    
    ###############################################################################
    # GUI and "global" variables (to be able to better integrate this into other code, an overall function was created, and instead of using "global" we always use "nonlocal" to not conflict with other functions)
    
    
    # global variables
    outputdata = pd.DataFrame()
    layer1WaterDistribution = defaultdict(dict)
    layer1WaterDistributionPercent = pd.DataFrame()
    
    # construct window
    mainWindow = tkinter.Tk()
    mainWindow.state('zoomed')
    #mainWindow.geometry("1300x700")
    
    # divide the window into left and right halfes
    menueBar = ttk.Frame(mainWindow) # area for input
    menueBar.pack(side="left", fill="y", expand=False)
    menueTabs = ttk.Notebook(menueBar) 
    menueTabs.pack(side="left", fill="y", expand=False)
    plotArea = ttk.Frame(mainWindow) # area for plots to go
    plotArea.pack(side="left", fill="both", expand=True)
    plotTabs = ttk.Notebook(plotArea) 
    plotTabs.pack(side="left", fill="both", expand=True)
    
    # eyecandy
    mainWindow.title("Infiltration- and runoffmodel")
    try: # icon eyecandy, in "try" so nothing breaks when the icon is missing
        windowIcon = tkinter.PhotoImage(file = "icon.png")
        mainWindow.iconphoto(False, windowIcon)
        logo = ttk.Label(menueBar, image=windowIcon, padding=10)
        logo.image = windowIcon
        logo.place(rely=1, relx=0.5, anchor="s")
    except:
        print("Cant find Logo image.")
    
    
    
    ###############################################################################
    # plots
    
    
    
    # Summary
    mainPlotTab = ttk.Frame(plotTabs) # frame
    mainPlotTab.pack(side="top", fill="both", expand=True)
    plotTabs.add(mainPlotTab, text="Summary")
    
    mainPlot = plt.figure.Figure() # the canvas for the plot togo on
    mainPlotWidget = FigureCanvasTkAgg(mainPlot, master=mainPlotTab) # integrate the canvas into tkinter
    mainPlotWidget.get_tk_widget().pack(side="top", fill="both", expand=True)
    
    mainSubplot = mainPlot.add_subplot() # create an empty plot so the window isnt empty on startup and the user knows what to expect
    mainSubplot.set(xlabel = "time [min]", ylabel = "Water Amount [mm]", title = "Summary")
    
    mainToolBarRestricor = ttk.Frame(mainPlotTab)
    mainToolBarRestricor.place(height=28, rely=1, anchor="sw")
    mainToolBar = NavigationToolbar2Tk(mainPlotWidget, mainToolBarRestricor, pack_toolbar=False)
    mainToolBar.pack(side="bottom")
    
    def UpdateMainPlot():
        mainPlot.clf() # clear all old stuff from the canvas
        mainSubplot = mainPlot.add_subplot() # create new plot to put things on
        mainSubplot.set(xlabel = "time [min]", ylabel = "Water Amount [mm]", title = "Summary")
        try: # this is in "try:" so when users use the checkboxes before generating data noting breaks
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
    detailIntensityPlot = plt.figure.Figure(layout='constrained', figsize=(1, 100/plt.rcParams['figure.dpi']), ) # the canvas for the plot to go on
    detailIntensityPlotWidget = FigureCanvasTkAgg(detailIntensityPlot, master=detailIntensityFrame) # integrate the canvas into tkinter
    detailIntensityPlotWidget.get_tk_widget().pack(side="left", fill="x", expand=True)
    detailIntensityLine = plt.lines.Line2D((),(), color="magenta") # these variables hold the data that gets changed when moving the tim controler -> this is faster and more responsive then deleting everything an plotting it new
    detailIntensityLabelMin = tkinter.Label(detailIntensityFrame, text="time [min]", background="white", font=("Helvetica", 12))
    detailIntensityLabelMin.place(anchor="se", rely=0.9, relx=1)
    detailIntensitySubplot = detailIntensityPlot.add_subplot() # create an empty plot so the window isnt empty on startup and the user knows what to expect
    detailIntensitySubplot.set(ylabel = "[mm]")    
    
    
    detailControlerFrame = ttk.Frame(detailPlotTab)
    detailControlerFrame.pack(side="top", fill="x")
    detailPlot = plt.figure.Figure(layout='constrained') # the canvas for the plot to go on
    detailPlotWidget = FigureCanvasTkAgg(detailPlot, master=detailPlotTab) # integrate the canvas into tkinter
    detailPlotWidget.get_tk_widget().pack(side="top", fill="both", expand=True)

    
    # initiale variablen damit beim ersten mal nix fehler prodoziert
    detailMinuteLabel = tkinter.Label(detailControlerFrame, text="Minute:", font=("Helvetica", 11, "bold"))
    detailMinuteLabel.pack(side="left", padx=5)
    detailPlotControler = ttk.Scale(detailControlerFrame) # create a dummy controler so it can be destroid when doing the first simulation and not cause errors
    detailPlotControler.pack(side="left", fill="x", padx=5, expand=True)
    detailPlotLine = plt.lines.Line2D((),()) # these variables hold the data that gets changed when moving the tim controler -> this is faster and more responsive then deleting everything an plotting it new
    detailWaterDistributionSubplot = detailPlot.add_subplot() # create an empty plot so the window isnt empty on startup and the user knows what to expect
    detailWaterDistributionSubplot.set(xlabel = "Water Amount [Volume/Volume]", ylabel = "Depth below Surface [mm]", title = "Water Distribution within Upper Layer at Minute 0")
    
    
    def ScrollDetailPlot(timeIndex):
        timeIndex = float(timeIndex) # this value is a string from the widged -> need to convert it into int
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
    
    
    # create the file line on the top right
    fileFrame = ttk.Frame(plotArea)
    fileFrame.place(rely=0, relx=1, anchor="ne")
    filePathBox = ttk.Entry(fileFrame, width=40)
    filePathBox.pack(side="right", padx=10)
    filePathBox.insert(0, "No File Selected")
    filePathLabel = ttk.Label(fileFrame, text = "Path to CSV File:")
    filePathLabel.pack(side="right")
    
    
    
    ###############################################################################
    # input 
    
    
    inputMenueTab = ttk.Frame(menueTabs) # frame
    inputMenueTab.pack(side="left", fill="y", expand=False)
    menueTabs.add(inputMenueTab, text="Input")
    
        # create the file input in inputMenueTab
    inputFileFrame = ttk.LabelFrame(inputMenueTab, text="Input File", borderwidth=5)
    inputFileFrame.pack(side="top", padx=5, pady=5, fill="x")
    inpuFileButtonFrame = ttk.Frame(inputFileFrame)
    inpuFileButtonFrame.pack(side="top", pady=5, fill="x")
    def ChooseInputFile(): # the function that makes the popup apear to select a file
        inputFilePath = tkinter.filedialog.askopenfilename(initialdir = "/", title = "Select Input CSV File", filetypes = (("csv files","*.CSV"), ("all files","*.*")))
        filePathBox.delete(0,'end')
        filePathBox.insert(0, inputFilePath)
        print (inputFilePath)
    inputSelectButton = ttk.Button(inpuFileButtonFrame, text="Choose CSV", command=ChooseInputFile)
    inputSelectButton.pack(side="left")
    
        # the unit help window explainer thingy
    def InputUnitFactorExplainer():
        inputPopup = tkinter.Toplevel(mainWindow)
        inputPopup.title("Information")
        inputPopupLabel = ttk.Label(inputPopup, justify="left", text= 'This model assumes all data to be resolved in minutes. Any data that is not resolved in minutes might lead to unpredictable behaviour. All parameters given via the GUI (like hydraulic conductivity, evaporation, ...) are assumed to be constant over the entire simulation of the model.', wraplength=300)
        inputPopupLabel.pack(padx=30, pady=30)
        inputPopupLabel = ttk.Label(inputPopup, justify="left", text= 'If your CSV input file has a different unit then millimeter resolved per minute, you can enter a factor in "Unit Correction Factor" to convert your data into [mm/min]. EXAMPLE: Your CSV data is in [inch/min], so 25.4 is entered as a correction factor to archive [mm/min].', wraplength=300)
        inputPopupLabel.pack(padx=30, pady=0)
        inputPopupLabel = ttk.Label(inputPopup, justify="left", text= 'Any units shown as [Volume/Volume] are referring to a volume fraction of the sorrounding soil, so 100% = 1, 50% = 0.5 and 0% = 0.', wraplength=300)
        inputPopupLabel.pack(padx=30, pady=30)
    inputUnitFactorExplainer = ttk.Button(inpuFileButtonFrame, text="Help with Units", command=InputUnitFactorExplainer)
    inputUnitFactorExplainer.pack(side="right")
    
        # the CSV seperator
    inputSeperatorFrame = ttk.Frame(inputFileFrame)
    inputSeperatorFrame.pack(side="top", pady=5, fill="x")
    inputSeperatorLabel = ttk.Label(inputSeperatorFrame, text="Value Seperator")
    inputSeperatorLabel.pack(side="left")
    inputSeperatorBox = ttk.Entry(inputSeperatorFrame, width=8)
    inputSeperatorBox.insert(0, ",")
    inputSeperatorBox.pack(side="right")
        # the CSV column to use
    inputColumnFrame = ttk.Frame(inputFileFrame)
    inputColumnFrame.pack(side="top", pady=5, fill="x")
    inputColumnNameLabel = ttk.Label(inputColumnFrame, text="Column with [intensity/min] Data")#, wraplength=110)
    inputColumnNameLabel.pack(side="top", fill="x")
    inputColumnNameBox = ttk.Entry(inputColumnFrame, width=30)
    inputColumnNameBox.pack(side="top", fill="x")
        # correction factor if the unit in CSV is of
    inputUnitFactorFrame = ttk.Frame(inputFileFrame)
    inputUnitFactorFrame.pack(side="top", pady=5, fill="x")
    inputUnitFactorLabel = ttk.Label(inputUnitFactorFrame, text="Unit Correction Factor")#, wraplength=110)
    inputUnitFactorLabel.pack(side="top", fill="x")
    inputUnitFactorBox = ttk.Entry(inputUnitFactorFrame, width=8)
    inputUnitFactorBox.insert(0, 1)
    inputUnitFactorBox.place(anchor="ne", relx=1, rely=0)
    
    # parameters for layer 1
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
    
    
    # parameters for the model boundary
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
    

    
    
    # start and export buttons and functions
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
            layer1WaterDistributionPercent.iloc[::-1].transpose().to_csv(file) # reverse the order and swapp the axis so that the sublayers are descending and the rows are for time
            file.close()
    inputSelectButton = ttk.Button(inputMenueTab, text="Export Sublayer Data [Volume/Volume]", command=ExportUperLayerData)
    inputSelectButton.pack(side="top", padx=10, pady=5)
    
    
    
    #######################################################################################
    # Plot control tab - a bunch of checkboxes that turn variables true/false for the sumary plot update function to use
    
    
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
        
        #RunSimulation()
        
    #DebugValues()
    
    
    
    
    # Updaten
    mainWindow.mainloop()
    
InflitrationModel()
