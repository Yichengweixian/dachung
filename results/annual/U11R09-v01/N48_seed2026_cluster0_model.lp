\* U06_master_continuous_LP *\
Minimize
OBJ: 10 discharge_0000 + 10 discharge_0001 + 10 discharge_0002
 + 10 discharge_0003 + 10 discharge_0004 + 10 discharge_0005
 + 10 discharge_0006 + 10 discharge_0007 + 10 discharge_0008
 + 10 discharge_0009 + 10 discharge_0010 + 10 discharge_0011
 + 10 discharge_0012 + 10 discharge_0013 + 10 discharge_0014
 + 10 discharge_0015 + 10 discharge_0016 + 10 discharge_0017
 + 10 discharge_0018 + 10 discharge_0019 + 10 discharge_0020
 + 10 discharge_0021 + 10 discharge_0022 + 10 discharge_0023
 + 200 solar_curt_0000 + 200 solar_curt_0001 + 200 solar_curt_0002
 + 200 solar_curt_0003 + 200 solar_curt_0004 + 200 solar_curt_0005
 + 200 solar_curt_0006 + 200 solar_curt_0007 + 200 solar_curt_0008
 + 200 solar_curt_0009 + 200 solar_curt_0010 + 200 solar_curt_0011
 + 200 solar_curt_0012 + 200 solar_curt_0013 + 200 solar_curt_0014
 + 200 solar_curt_0015 + 200 solar_curt_0016 + 200 solar_curt_0017
 + 200 solar_curt_0018 + 200 solar_curt_0019 + 200 solar_curt_0020
 + 200 solar_curt_0021 + 200 solar_curt_0022 + 200 solar_curt_0023
 + 350 thermal_0000 + 350 thermal_0001 + 350 thermal_0002 + 350 thermal_0003
 + 350 thermal_0004 + 350 thermal_0005 + 350 thermal_0006 + 350 thermal_0007
 + 350 thermal_0008 + 350 thermal_0009 + 350 thermal_0010 + 350 thermal_0011
 + 350 thermal_0012 + 350 thermal_0013 + 350 thermal_0014 + 350 thermal_0015
 + 350 thermal_0016 + 350 thermal_0017 + 350 thermal_0018 + 350 thermal_0019
 + 350 thermal_0020 + 350 thermal_0021 + 350 thermal_0022 + 350 thermal_0023
 + 10000 unserved_0000 + 10000 unserved_0001 + 10000 unserved_0002
 + 10000 unserved_0003 + 10000 unserved_0004 + 10000 unserved_0005
 + 10000 unserved_0006 + 10000 unserved_0007 + 10000 unserved_0008
 + 10000 unserved_0009 + 10000 unserved_0010 + 10000 unserved_0011
 + 10000 unserved_0012 + 10000 unserved_0013 + 10000 unserved_0014
 + 10000 unserved_0015 + 10000 unserved_0016 + 10000 unserved_0017
 + 10000 unserved_0018 + 10000 unserved_0019 + 10000 unserved_0020
 + 10000 unserved_0021 + 10000 unserved_0022 + 10000 unserved_0023
 + 200 wind_curt_0000 + 200 wind_curt_0001 + 200 wind_curt_0002
 + 200 wind_curt_0003 + 200 wind_curt_0004 + 200 wind_curt_0005
 + 200 wind_curt_0006 + 200 wind_curt_0007 + 200 wind_curt_0008
 + 200 wind_curt_0009 + 200 wind_curt_0010 + 200 wind_curt_0011
 + 200 wind_curt_0012 + 200 wind_curt_0013 + 200 wind_curt_0014
 + 200 wind_curt_0015 + 200 wind_curt_0016 + 200 wind_curt_0017
 + 200 wind_curt_0018 + 200 wind_curt_0019 + 200 wind_curt_0020
 + 200 wind_curt_0021 + 200 wind_curt_0022 + 200 wind_curt_0023
Subject To
_C1: energy_0000 = 20
_C10: charge_0000 - 20 charge_mode_0000 <= 0
_C100: discharge_0007 <= 20
_C101: charge_0007 - 20 charge_mode_0007 <= 0
_C102: 20 charge_mode_0007 + discharge_0007 <= 20
_C103: - 0.95 charge_0007 + 1.05263157895 discharge_0007 - energy_0007
 + energy_0008 = 0
_C104: - charge_0007 + discharge_0007 + solar_used_0007 + thermal_0007
 + unserved_0007 + wind_used_0007 = 122
_C105: thermal_0008 >= 30
_C106: thermal_0008 <= 120
_C107: - thermal_0007 + thermal_0008 <= 30
_C108: - thermal_0007 + thermal_0008 >= -30
_C109: wind_curt_0008 + wind_used_0008 = 4.06
_C11: 20 charge_mode_0000 + discharge_0000 <= 20
_C110: solar_curt_0008 + solar_used_0008 = 14.25
_C111: unserved_0008 <= 139
_C112: charge_0008 <= 20
_C113: discharge_0008 <= 20
_C114: charge_0008 - 20 charge_mode_0008 <= 0
_C115: 20 charge_mode_0008 + discharge_0008 <= 20
_C116: - 0.95 charge_0008 + 1.05263157895 discharge_0008 - energy_0008
 + energy_0009 = 0
_C117: - charge_0008 + discharge_0008 + solar_used_0008 + thermal_0008
 + unserved_0008 + wind_used_0008 = 139
_C118: thermal_0009 >= 30
_C119: thermal_0009 <= 120
_C12: - 0.95 charge_0000 + 1.05263157895 discharge_0000 - energy_0000
 + energy_0001 = 0
_C120: - thermal_0008 + thermal_0009 <= 30
_C121: - thermal_0008 + thermal_0009 >= -30
_C122: wind_curt_0009 + wind_used_0009 = 6.58
_C123: solar_curt_0009 + solar_used_0009 = 0
_C124: unserved_0009 <= 145
_C125: charge_0009 <= 20
_C126: discharge_0009 <= 20
_C127: charge_0009 - 20 charge_mode_0009 <= 0
_C128: 20 charge_mode_0009 + discharge_0009 <= 20
_C129: - 0.95 charge_0009 + 1.05263157895 discharge_0009 - energy_0009
 + energy_0010 = 0
_C13: - charge_0000 + discharge_0000 + solar_used_0000 + thermal_0000
 + unserved_0000 + wind_used_0000 = 92
_C130: - charge_0009 + discharge_0009 + solar_used_0009 + thermal_0009
 + unserved_0009 + wind_used_0009 = 145
_C131: thermal_0010 >= 30
_C132: thermal_0010 <= 120
_C133: - thermal_0009 + thermal_0010 <= 30
_C134: - thermal_0009 + thermal_0010 >= -30
_C135: wind_curt_0010 + wind_used_0010 = 11.89
_C136: solar_curt_0010 + solar_used_0010 = 0
_C137: unserved_0010 <= 141
_C138: charge_0010 <= 20
_C139: discharge_0010 <= 20
_C14: thermal_0001 >= 30
_C140: charge_0010 - 20 charge_mode_0010 <= 0
_C141: 20 charge_mode_0010 + discharge_0010 <= 20
_C142: - 0.95 charge_0010 + 1.05263157895 discharge_0010 - energy_0010
 + energy_0011 = 0
_C143: - charge_0010 + discharge_0010 + solar_used_0010 + thermal_0010
 + unserved_0010 + wind_used_0010 = 141
_C144: thermal_0011 >= 30
_C145: thermal_0011 <= 120
_C146: - thermal_0010 + thermal_0011 <= 30
_C147: - thermal_0010 + thermal_0011 >= -30
_C148: wind_curt_0011 + wind_used_0011 = 18.15
_C149: solar_curt_0011 + solar_used_0011 = 0
_C15: thermal_0001 <= 120
_C150: unserved_0011 <= 134
_C151: charge_0011 <= 20
_C152: discharge_0011 <= 20
_C153: charge_0011 - 20 charge_mode_0011 <= 0
_C154: 20 charge_mode_0011 + discharge_0011 <= 20
_C155: - 0.95 charge_0011 + 1.05263157895 discharge_0011 - energy_0011
 + energy_0012 = 0
_C156: - charge_0011 + discharge_0011 + solar_used_0011 + thermal_0011
 + unserved_0011 + wind_used_0011 = 134
_C157: thermal_0012 >= 30
_C158: thermal_0012 <= 120
_C159: - thermal_0011 + thermal_0012 <= 30
_C16: - thermal_0000 + thermal_0001 <= 30
_C160: - thermal_0011 + thermal_0012 >= -30
_C161: wind_curt_0012 + wind_used_0012 = 19.54
_C162: solar_curt_0012 + solar_used_0012 = 0
_C163: unserved_0012 <= 128
_C164: charge_0012 <= 20
_C165: discharge_0012 <= 20
_C166: charge_0012 - 20 charge_mode_0012 <= 0
_C167: 20 charge_mode_0012 + discharge_0012 <= 20
_C168: - 0.95 charge_0012 + 1.05263157895 discharge_0012 - energy_0012
 + energy_0013 = 0
_C169: - charge_0012 + discharge_0012 + solar_used_0012 + thermal_0012
 + unserved_0012 + wind_used_0012 = 128
_C17: - thermal_0000 + thermal_0001 >= -30
_C170: thermal_0013 >= 30
_C171: thermal_0013 <= 120
_C172: - thermal_0012 + thermal_0013 <= 30
_C173: - thermal_0012 + thermal_0013 >= -30
_C174: wind_curt_0013 + wind_used_0013 = 16.09
_C175: solar_curt_0013 + solar_used_0013 = 0
_C176: unserved_0013 <= 125
_C177: charge_0013 <= 20
_C178: discharge_0013 <= 20
_C179: charge_0013 - 20 charge_mode_0013 <= 0
_C18: wind_curt_0001 + wind_used_0001 = 2.61
_C180: 20 charge_mode_0013 + discharge_0013 <= 20
_C181: - 0.95 charge_0013 + 1.05263157895 discharge_0013 - energy_0013
 + energy_0014 = 0
_C182: - charge_0013 + discharge_0013 + solar_used_0013 + thermal_0013
 + unserved_0013 + wind_used_0013 = 125
_C183: thermal_0014 >= 30
_C184: thermal_0014 <= 120
_C185: - thermal_0013 + thermal_0014 <= 30
_C186: - thermal_0013 + thermal_0014 >= -30
_C187: wind_curt_0014 + wind_used_0014 = 12.09
_C188: solar_curt_0014 + solar_used_0014 = 0
_C189: unserved_0014 <= 127
_C19: solar_curt_0001 + solar_used_0001 = 57.91
_C190: charge_0014 <= 20
_C191: discharge_0014 <= 20
_C192: charge_0014 - 20 charge_mode_0014 <= 0
_C193: 20 charge_mode_0014 + discharge_0014 <= 20
_C194: - 0.95 charge_0014 + 1.05263157895 discharge_0014 - energy_0014
 + energy_0015 = 0
_C195: - charge_0014 + discharge_0014 + solar_used_0014 + thermal_0014
 + unserved_0014 + wind_used_0014 = 127
_C196: thermal_0015 >= 30
_C197: thermal_0015 <= 120
_C198: - thermal_0014 + thermal_0015 <= 30
_C199: - thermal_0014 + thermal_0015 >= -30
_C2: - energy_0000 + energy_0024 = 0
_C20: unserved_0001 <= 87
_C200: wind_curt_0015 + wind_used_0015 = 9.88
_C201: solar_curt_0015 + solar_used_0015 = 0
_C202: unserved_0015 <= 133
_C203: charge_0015 <= 20
_C204: discharge_0015 <= 20
_C205: charge_0015 - 20 charge_mode_0015 <= 0
_C206: 20 charge_mode_0015 + discharge_0015 <= 20
_C207: - 0.95 charge_0015 + 1.05263157895 discharge_0015 - energy_0015
 + energy_0016 = 0
_C208: - charge_0015 + discharge_0015 + solar_used_0015 + thermal_0015
 + unserved_0015 + wind_used_0015 = 133
_C209: thermal_0016 >= 30
_C21: charge_0001 <= 20
_C210: thermal_0016 <= 120
_C211: - thermal_0015 + thermal_0016 <= 30
_C212: - thermal_0015 + thermal_0016 >= -30
_C213: wind_curt_0016 + wind_used_0016 = 8.63
_C214: solar_curt_0016 + solar_used_0016 = 0
_C215: unserved_0016 <= 143
_C216: charge_0016 <= 20
_C217: discharge_0016 <= 20
_C218: charge_0016 - 20 charge_mode_0016 <= 0
_C219: 20 charge_mode_0016 + discharge_0016 <= 20
_C22: discharge_0001 <= 20
_C220: - 0.95 charge_0016 + 1.05263157895 discharge_0016 - energy_0016
 + energy_0017 = 0
_C221: - charge_0016 + discharge_0016 + solar_used_0016 + thermal_0016
 + unserved_0016 + wind_used_0016 = 143
_C222: thermal_0017 >= 30
_C223: thermal_0017 <= 120
_C224: - thermal_0016 + thermal_0017 <= 30
_C225: - thermal_0016 + thermal_0017 >= -30
_C226: wind_curt_0017 + wind_used_0017 = 7.98
_C227: solar_curt_0017 + solar_used_0017 = 0
_C228: unserved_0017 <= 154
_C229: charge_0017 <= 20
_C23: charge_0001 - 20 charge_mode_0001 <= 0
_C230: discharge_0017 <= 20
_C231: charge_0017 - 20 charge_mode_0017 <= 0
_C232: 20 charge_mode_0017 + discharge_0017 <= 20
_C233: - 0.95 charge_0017 + 1.05263157895 discharge_0017 - energy_0017
 + energy_0018 = 0
_C234: - charge_0017 + discharge_0017 + solar_used_0017 + thermal_0017
 + unserved_0017 + wind_used_0017 = 154
_C235: thermal_0018 >= 30
_C236: thermal_0018 <= 120
_C237: - thermal_0017 + thermal_0018 <= 30
_C238: - thermal_0017 + thermal_0018 >= -30
_C239: wind_curt_0018 + wind_used_0018 = 6.26
_C24: 20 charge_mode_0001 + discharge_0001 <= 20
_C240: solar_curt_0018 + solar_used_0018 = 0
_C241: unserved_0018 <= 160
_C242: charge_0018 <= 20
_C243: discharge_0018 <= 20
_C244: charge_0018 - 20 charge_mode_0018 <= 0
_C245: 20 charge_mode_0018 + discharge_0018 <= 20
_C246: - 0.95 charge_0018 + 1.05263157895 discharge_0018 - energy_0018
 + energy_0019 = 0
_C247: - charge_0018 + discharge_0018 + solar_used_0018 + thermal_0018
 + unserved_0018 + wind_used_0018 = 160
_C248: thermal_0019 >= 30
_C249: thermal_0019 <= 120
_C25: - 0.95 charge_0001 + 1.05263157895 discharge_0001 - energy_0001
 + energy_0002 = 0
_C250: - thermal_0018 + thermal_0019 <= 30
_C251: - thermal_0018 + thermal_0019 >= -30
_C252: wind_curt_0019 + wind_used_0019 = 3.19
_C253: solar_curt_0019 + solar_used_0019 = 0
_C254: unserved_0019 <= 162
_C255: charge_0019 <= 20
_C256: discharge_0019 <= 20
_C257: charge_0019 - 20 charge_mode_0019 <= 0
_C258: 20 charge_mode_0019 + discharge_0019 <= 20
_C259: - 0.95 charge_0019 + 1.05263157895 discharge_0019 - energy_0019
 + energy_0020 = 0
_C26: - charge_0001 + discharge_0001 + solar_used_0001 + thermal_0001
 + unserved_0001 + wind_used_0001 = 87
_C260: - charge_0019 + discharge_0019 + solar_used_0019 + thermal_0019
 + unserved_0019 + wind_used_0019 = 162
_C261: thermal_0020 >= 30
_C262: thermal_0020 <= 120
_C263: - thermal_0019 + thermal_0020 <= 30
_C264: - thermal_0019 + thermal_0020 >= -30
_C265: wind_curt_0020 + wind_used_0020 = 0.39
_C266: solar_curt_0020 + solar_used_0020 = 0
_C267: unserved_0020 <= 151
_C268: charge_0020 <= 20
_C269: discharge_0020 <= 20
_C27: thermal_0002 >= 30
_C270: charge_0020 - 20 charge_mode_0020 <= 0
_C271: 20 charge_mode_0020 + discharge_0020 <= 20
_C272: - 0.95 charge_0020 + 1.05263157895 discharge_0020 - energy_0020
 + energy_0021 = 0
_C273: - charge_0020 + discharge_0020 + solar_used_0020 + thermal_0020
 + unserved_0020 + wind_used_0020 = 151
_C274: thermal_0021 >= 30
_C275: thermal_0021 <= 120
_C276: - thermal_0020 + thermal_0021 <= 30
_C277: - thermal_0020 + thermal_0021 >= -30
_C278: wind_curt_0021 + wind_used_0021 = 0
_C279: solar_curt_0021 + solar_used_0021 = 0
_C28: thermal_0002 <= 120
_C280: unserved_0021 <= 132
_C281: charge_0021 <= 20
_C282: discharge_0021 <= 20
_C283: charge_0021 - 20 charge_mode_0021 <= 0
_C284: 20 charge_mode_0021 + discharge_0021 <= 20
_C285: - 0.95 charge_0021 + 1.05263157895 discharge_0021 - energy_0021
 + energy_0022 = 0
_C286: - charge_0021 + discharge_0021 + solar_used_0021 + thermal_0021
 + unserved_0021 + wind_used_0021 = 132
_C287: thermal_0022 >= 30
_C288: thermal_0022 <= 120
_C289: - thermal_0021 + thermal_0022 <= 30
_C29: - thermal_0001 + thermal_0002 <= 30
_C290: - thermal_0021 + thermal_0022 >= -30
_C291: wind_curt_0022 + wind_used_0022 = 0
_C292: solar_curt_0022 + solar_used_0022 = 0
_C293: unserved_0022 <= 112
_C294: charge_0022 <= 20
_C295: discharge_0022 <= 20
_C296: charge_0022 - 20 charge_mode_0022 <= 0
_C297: 20 charge_mode_0022 + discharge_0022 <= 20
_C298: - 0.95 charge_0022 + 1.05263157895 discharge_0022 - energy_0022
 + energy_0023 = 0
_C299: - charge_0022 + discharge_0022 + solar_used_0022 + thermal_0022
 + unserved_0022 + wind_used_0022 = 112
_C3: thermal_0000 >= 30
_C30: - thermal_0001 + thermal_0002 >= -30
_C300: thermal_0023 >= 30
_C301: thermal_0023 <= 120
_C302: - thermal_0022 + thermal_0023 <= 30
_C303: - thermal_0022 + thermal_0023 >= -30
_C304: wind_curt_0023 + wind_used_0023 = 0
_C305: solar_curt_0023 + solar_used_0023 = 5.02
_C306: unserved_0023 <= 99
_C307: charge_0023 <= 20
_C308: discharge_0023 <= 20
_C309: charge_0023 - 20 charge_mode_0023 <= 0
_C31: wind_curt_0002 + wind_used_0002 = 12.02
_C310: 20 charge_mode_0023 + discharge_0023 <= 20
_C311: - 0.95 charge_0023 + 1.05263157895 discharge_0023 - energy_0023
 + energy_0024 = 0
_C312: - charge_0023 + discharge_0023 + solar_used_0023 + thermal_0023
 + unserved_0023 + wind_used_0023 = 99
_C32: solar_curt_0002 + solar_used_0002 = 77.35
_C33: unserved_0002 <= 83
_C34: charge_0002 <= 20
_C35: discharge_0002 <= 20
_C36: charge_0002 - 20 charge_mode_0002 <= 0
_C37: 20 charge_mode_0002 + discharge_0002 <= 20
_C38: - 0.95 charge_0002 + 1.05263157895 discharge_0002 - energy_0002
 + energy_0003 = 0
_C39: - charge_0002 + discharge_0002 + solar_used_0002 + thermal_0002
 + unserved_0002 + wind_used_0002 = 83
_C4: thermal_0000 <= 120
_C40: thermal_0003 >= 30
_C41: thermal_0003 <= 120
_C42: - thermal_0002 + thermal_0003 <= 30
_C43: - thermal_0002 + thermal_0003 >= -30
_C44: wind_curt_0003 + wind_used_0003 = 21.47
_C45: solar_curt_0003 + solar_used_0003 = 88.03
_C46: unserved_0003 <= 81
_C47: charge_0003 <= 20
_C48: discharge_0003 <= 20
_C49: charge_0003 - 20 charge_mode_0003 <= 0
_C5: wind_curt_0000 + wind_used_0000 = 1.59
_C50: 20 charge_mode_0003 + discharge_0003 <= 20
_C51: - 0.95 charge_0003 + 1.05263157895 discharge_0003 - energy_0003
 + energy_0004 = 0
_C52: - charge_0003 + discharge_0003 + solar_used_0003 + thermal_0003
 + unserved_0003 + wind_used_0003 = 81
_C53: thermal_0004 >= 30
_C54: thermal_0004 <= 120
_C55: - thermal_0003 + thermal_0004 <= 30
_C56: - thermal_0003 + thermal_0004 >= -30
_C57: wind_curt_0004 + wind_used_0004 = 17.98
_C58: solar_curt_0004 + solar_used_0004 = 91.57
_C59: unserved_0004 <= 82
_C6: solar_curt_0000 + solar_used_0000 = 33.04
_C60: charge_0004 <= 20
_C61: discharge_0004 <= 20
_C62: charge_0004 - 20 charge_mode_0004 <= 0
_C63: 20 charge_mode_0004 + discharge_0004 <= 20
_C64: - 0.95 charge_0004 + 1.05263157895 discharge_0004 - energy_0004
 + energy_0005 = 0
_C65: - charge_0004 + discharge_0004 + solar_used_0004 + thermal_0004
 + unserved_0004 + wind_used_0004 = 82
_C66: thermal_0005 >= 30
_C67: thermal_0005 <= 120
_C68: - thermal_0004 + thermal_0005 <= 30
_C69: - thermal_0004 + thermal_0005 >= -30
_C7: unserved_0000 <= 92
_C70: wind_curt_0005 + wind_used_0005 = 12.02
_C71: solar_curt_0005 + solar_used_0005 = 81.8
_C72: unserved_0005 <= 89
_C73: charge_0005 <= 20
_C74: discharge_0005 <= 20
_C75: charge_0005 - 20 charge_mode_0005 <= 0
_C76: 20 charge_mode_0005 + discharge_0005 <= 20
_C77: - 0.95 charge_0005 + 1.05263157895 discharge_0005 - energy_0005
 + energy_0006 = 0
_C78: - charge_0005 + discharge_0005 + solar_used_0005 + thermal_0005
 + unserved_0005 + wind_used_0005 = 89
_C79: thermal_0006 >= 30
_C8: charge_0000 <= 20
_C80: thermal_0006 <= 120
_C81: - thermal_0005 + thermal_0006 <= 30
_C82: - thermal_0005 + thermal_0006 >= -30
_C83: wind_curt_0006 + wind_used_0006 = 8.68
_C84: solar_curt_0006 + solar_used_0006 = 63.83
_C85: unserved_0006 <= 103
_C86: charge_0006 <= 20
_C87: discharge_0006 <= 20
_C88: charge_0006 - 20 charge_mode_0006 <= 0
_C89: 20 charge_mode_0006 + discharge_0006 <= 20
_C9: discharge_0000 <= 20
_C90: - 0.95 charge_0006 + 1.05263157895 discharge_0006 - energy_0006
 + energy_0007 = 0
_C91: - charge_0006 + discharge_0006 + solar_used_0006 + thermal_0006
 + unserved_0006 + wind_used_0006 = 103
_C92: thermal_0007 >= 30
_C93: thermal_0007 <= 120
_C94: - thermal_0006 + thermal_0007 <= 30
_C95: - thermal_0006 + thermal_0007 >= -30
_C96: wind_curt_0007 + wind_used_0007 = 6.12
_C97: solar_curt_0007 + solar_used_0007 = 39.21
_C98: unserved_0007 <= 122
_C99: charge_0007 <= 20
Bounds
 4 <= energy_0000 <= 36
 4 <= energy_0001 <= 36
 4 <= energy_0002 <= 36
 4 <= energy_0003 <= 36
 4 <= energy_0004 <= 36
 4 <= energy_0005 <= 36
 4 <= energy_0006 <= 36
 4 <= energy_0007 <= 36
 4 <= energy_0008 <= 36
 4 <= energy_0009 <= 36
 4 <= energy_0010 <= 36
 4 <= energy_0011 <= 36
 4 <= energy_0012 <= 36
 4 <= energy_0013 <= 36
 4 <= energy_0014 <= 36
 4 <= energy_0015 <= 36
 4 <= energy_0016 <= 36
 4 <= energy_0017 <= 36
 4 <= energy_0018 <= 36
 4 <= energy_0019 <= 36
 4 <= energy_0020 <= 36
 4 <= energy_0021 <= 36
 4 <= energy_0022 <= 36
 4 <= energy_0023 <= 36
 4 <= energy_0024 <= 36
Binaries
charge_mode_0000
charge_mode_0001
charge_mode_0002
charge_mode_0003
charge_mode_0004
charge_mode_0005
charge_mode_0006
charge_mode_0007
charge_mode_0008
charge_mode_0009
charge_mode_0010
charge_mode_0011
charge_mode_0012
charge_mode_0013
charge_mode_0014
charge_mode_0015
charge_mode_0016
charge_mode_0017
charge_mode_0018
charge_mode_0019
charge_mode_0020
charge_mode_0021
charge_mode_0022
charge_mode_0023
End
