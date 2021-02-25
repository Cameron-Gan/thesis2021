import thesisInitial.tariff as tf

peak        = {(6,10): 40.08, (15,1): 40.08}
shoulder    = {(10,15): 20.06}
off_peak    = {(1,6): 21.62}

tou_rate = {**peak, **shoulder, **off_peak}

fit =



OriginGO = tf.TOUTariff(73.71, 8, 'OriginGO', tou_rate)

