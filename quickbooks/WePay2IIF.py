#!/usr/bin/env python

import sys, os
import decimal
import csv

checkingAccount = "Account - Bank - MCB Checking"
bankAccount = "Account - Bank - WePay"
expenseAccount = "Expense - Bank - WePay"
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
    if i % 2 == 0:
        continue

    date = row[1]
    sender = row[2]
    amount = toFloat(row[11])
    fee = toFloat(row[12])
    net = toFloat(row[13])
    memo = row[14]

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
