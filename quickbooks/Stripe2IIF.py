#!/usr/bin/env python

import sys, os
import decimal
import csv

checkingAccount = "Account - Bank - MCB Checking"
bankAccount = "Account - Bank - Stripe"
expenseAccount = "Expense - Bank - Stripe"
incomeAccount = "Income - Donations - General" 

def toFloat(svalue):
    return float(svalue.replace(",", ""))

fp = None
try:
    fp = open(sys.argv[1], "r")
except IOError:
    print "Cannot open input file %s" % sys.argv[1]
    exit(0)

out = None
try:
    out = open(sys.argv[2], "w")
except IOError:
    print "Cannot open output file %s" % sys.argv[2]
    exit(0)

out.write('!TRNS\tDATE\tACCNT\tNAME\tCLASS\tAMOUNT\tMEMO\n')
out.write('!SPL\tDATE\tACCNT\tNAME\tAMOUNT\tMEMO\n')
out.write('!ENDTRNS\n')

trans = []
reader = csv.reader(fp)
for i, row in enumerate(reader):
    if not i:
        continue

    date = row[2].split(' ')[0]
    sender = row[24]
    amount = toFloat(row[6])
    fee = toFloat(row[8])
    net = amount - fee
    memo = row[1]

    if sender.startswith("Mission Community Bank"):
        toAccount = checkingAccount
    else:
        toAccount = incomeAccount

    out.write('TRNS\t"%s"\t"%s"\t"%s"\t"%s"\t%s\t"%s"\n' % (date, bankAccount, sender, "", net, memo))
    out.write('SPL\t"%s"\t"%s"\t"%s"\t%.2f\n' % (date, toAccount, sender, -amount))
    if fee > 0.0:
        out.write('SPL\t"%s"\t"%s"\tFee\t%.2f\n' % (date, expenseAccount, fee))
    out.write('ENDTRNS\n')

fp.close()
out.close()
