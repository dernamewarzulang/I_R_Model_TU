This is a tool that models surface layer infiltration.
It specifically focuses on the water movement in the top soil layer.

This model assumes all data to be resolved in minutes.
Any data that is not resolved in minutes might lead to unpredictable behaviour.
All parameters given via the GUI (like hydraulic conductivity, evaporation, ...) are assumed to be constant over the entire simulation of the model.

If your CSV input file has a different unit then millimeter resolved per minute, you can enter a factor in "Unit Correction Factor" to convert your data into [mm/min].
EXAMPLE: Your CSV data is in [inch/min], so 25.4 is entered as a correction factor to archive [mm/min].

Any input shown as [Volume/Volume] is referring to a volume fraction, so 100% = 1, 50% = 0.5 and 0% = 0
