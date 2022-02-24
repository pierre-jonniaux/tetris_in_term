#!/usr/bin/env python3
# -*- coding: utf-8 -*-
                            ###################
                            # TERMINAL TETRIS #
                            ###################

import os
import time
import curses
import sys
import random
import threading
import subprocess
# Une variable globale qui correspond aux changements de coord en fonction des
# fleches. Pas forcement necessaire mais mis au cas ou.
directions = {\
curses.KEY_LEFT : ( 0 ,-1),\
curses.KEY_RIGHT: ( 0 , 1),\
curses.KEY_DOWN : ( 1 , 0)\
}

# Le minuteur de la partie. Au lieu d'utiliser getch avec un delai (ecr.timout)
# ce qui pose certains problemes ("blocage" de la piece sur les bords en
# maintenant une direction, vitesse pas toujours uniforme...), on utilise un
# minuteur qui tourne dans un thread separe. Le truc fait descendre les pieces
# vers le bas a intervalle reguliers de maniere garantie. Rm: une classe est
# mieux qu'une def car plus pratique pour avoir un tempo specifique qui change.
# De plus avec une classe on peut start et stop le chrono facilement.
# RM: c'est le seul bout de code recupere sur le net (mais quand meme modifie)
# de tout le programme.
class chronometre:
    def __init__(self, tempo):
        self.tempo = tempo
        self.tictac = 0
        self.duree = 0
    # Avec une def, pour boucler on a besoin de refaire appel a soi meme et ben
    # la c'est pareil, la def run permet de se lancer soi meme.
    def run(self):
        # toutes les "durees de tempo", ca "run" et tictac alterne entre 1 & 0.
        self.tictac = 1 if self.tictac == 0 else 0
        self.duree  = self.duree + 1
        self.minuteur = threading.Timer(self.tempo, self.run)
        self.minuteur.start()
    
    def start(self):
        # Explication: "threading.Timer(X, def)" lance, sur une thread separee,
        # une fonction "def" au bout de X secondes.
        self.minuteur = threading.Timer(self.tempo, self.run)
        self.minuteur.start()

    def stop(self):
        # Le Timer de threading s'arrete avec ".cancel()": c'est comme ca.
        self.minuteur.cancel()

# La classe "etat_partie" defini plein de trucs dont
# - l'etat du terrain de jeu (self.hitbox) et ses dimensions
# - les score et la vitesse (le tempo de la classe chronometre)
# - les lignes completees a effacer (self.complete)
class etat_partie:
    def __init__(self):
        self.score    = 0
        self.vitesse  = 1
        self.niveau   = 0
        self.temps    = 0
        self.largeur  = 11
        self.hauteur  = 17
        self.couleur  = 2
        # hitbox = dico de la forme {(y,x) :'caractere'}
        self.hitbox   = {}
        # (index(y) des lignes completees)
        self.complete = {}
        self.piece_suivante =  forme_au_hasard()
        # Remplissage du terrain avec a chaque point cree, un espace blanc.
        for coord in [(y,x) for y in range(1,self.hauteur)
                            for x in range(1,self.largeur)]:
            self.hitbox[coord] = ' '
        def vitesseUp(self):
            self.vitesse = self.vitesse - 50

# La classe tetromino genere une nouvelle piece au hasard.
class tetromino():
    def __init__(self,nom,position = [0,3],orientation=0):
        # hitbox = dico de la forme {(y,x) :'caractere'}
        # La hitbox00 est la box 'absolue' par rapport a un point 0,0 en
        # utilisant le systeme de coordonees de curses.
        # L'autre est la hitbox a un instant T qui est, a chaque
        # deplacement, actualisee par rapport  a la 00 en fonction
        # de la nouvelle position.
        self.hitbox00        = {}
        self.hitbox          = {}
        # Position de depart de la piece (= haut-milieu du terrain par defaut)
        self.position = position
        # On assigne a la forme sa texture ainsi que sa "hitboxLoop" qui
        # defini et permet les rotations.
        #self.nom = 'carre'        # <- pour n'avoir que des carres pour debug.
        self.nom = nom
        
        if self.nom == 'carre':
            self.hitboxLoop = [ [(1,2),(1,3),(2,2),(2,3)] ]
            self.texture = '░'
            self.couleur = 6
        elif self.nom == 'ligne':
            self.texture = '█'
            self.hitboxLoop = [ [(1,1),(1,2),(1,3),(1,4)],
                                [(1,2),(2,2),(3,2),(4,2)] ]
            self.couleur = 7
        elif self.nom == 'Ldroit':
            self.texture = '▒'
            self.hitboxLoop = [ [(1,2),(2,2),(3,2),(3,3)],
                                [(2,1),(2,2),(2,3),(3,1)],
                                [(1,1),(1,2),(2,2),(3,2)],
                                [(1,3),(2,1),(2,2),(2,3)] ]
            self.couleur = 3
        elif self.nom == 'Lgauche':
            self.texture = '▓'
            self.hitboxLoop = [ [(1,2),(2,2),(3,2),(3,1)],
                                [(2,1),(2,2),(2,3),(1,1)],
                                [(1,3),(1,2),(2,2),(3,2)],
                                [(3,3),(2,1),(2,2),(2,3)] ]
            self.couleur = 4
        elif self.nom == 'Sdroit':
            self.texture = '▒'
            self.hitboxLoop = [ [(1,2),(1,3),(2,1),(2,2)],
                                [(1,2),(2,2),(2,3),(3,3)] ]
            self.couleur = 5
        elif self.nom == 'Sgauche':
            self.texture = '▓'
            self.hitboxLoop = [ [(1,1),(1,2),(2,2),(2,3)],
                                [(1,3),(2,2),(2,3),(3,2)] ]
            self.couleur = 8
        elif self.nom == 'triangle':
            self.texture = '█'
            self.hitboxLoop = [ [(1,2),(2,1),(2,2),(2,3)],
                                [(1,2),(3,2),(2,2),(2,3)],
                                [(3,2),(2,1),(2,2),(2,3)],
                                [(1,2),(2,1),(2,2),(3,2)] ]
            self.couleur = 8
        # Mega astuce dont je suis fier: pour boucler "a l'infini" a travers
        # les different item de hitboxLoop meme si l'index (orientation) est
        # trop grand ou trop petit on prend le reste de la division de l'index
        # en question par le nombre d'items.
        self.orientation = orientation%len(self.hitboxLoop)

        # Creation des 2 hitbox
        for coord in self.hitboxLoop[self.orientation]:
            self.hitbox00[coord]                     = self.texture
            self.hitbox[(coord[0]+self.position[0],
                         coord[1]+self.position[1])] = self.texture

    # recalcule les 2 hitboxes quand changement de position ou de hitbox00
    def maj_hitboxes(self):
        for coord in self.hitboxLoop[0]:
            self.hitbox00[coord]                     = self.texture
            self.hitbox[(coord[0]+self.position[0],
                         coord[1]+self.position[1])] = self.texture
       
    # Calcule, en fonction du deplacement, la hitbox en devenir...
    def deplacement_vers(self,pos):
        coinDepart = tuple(pos)
        #nexthitbox = {}
        for coord00 in self.hitbox00.keys():
            newpos = tuple([sum(z)for z in zip(coinDepart,coord00)])
            self.next_hitbox[newpos] = str(self.hitbox00[coord00])
            self.next_position = pos
    def pivote_a_droite(self):
        # On met la premiere hitbox de la liste a la fin
        self.hitboxLoop = self.hitboxLoop[1:]+self.hitboxLoop[:1]
        for coord in self.hitboxLoop[0]:
            self.next_hitbox[coord] = self.texture
    def pivote_a_gauche(self):
        # On met la derniere hitbox de la liste au debut
        self.hitboxLoop = self.hitboxLoop[-1:]+self.hitboxLoop[:-1]
        for coord in self.hitboxLoop[0]:
            self.next_hitbox[coord] = self.texture

# Un nom de forme au hasard (necessaire car la class tetromino requiert un nom)
def forme_au_hasard():
    forme = random.choice( ['carre'  , 'ligne'  , 'triangle' ,
                            'Ldroit' , 'Lgauche', 'Sdroit' , 'Sgauche',] )
    return forme

# Calcul si collision ou pas (entre piece et bord & entre piece et partie)
def collision(partie,piece):
    # Verifie qu'on est dans le field.
    # (cad forcement 4 keys-position en commun sinon ca depasse des bords
    if len( set(piece.hitbox.keys()) & set(partie.hitbox.keys()) ) !=4:
        return True
    # Verifie qu'on est pas sur un bloc (cad les 4 blocs en commun sont blancs)
    elif [partie.hitbox[coord] for coord in piece.hitbox.keys()] != [' ',' ',' ',' ']:
        return True
    else:
        return False

# La def pour faire descendre une piece calculer si elle peut ou pas,
# si elle doit se caler et faire reaparaitre une autre ou pas
# et si oui si ya game over... ou pas!
def descente(ecr,partie,piece,chrono_jeu):
    global directions
    key = curses.KEY_DOWN
    nextposition = [piece.position[0] + directions[key][0] ,
                    piece.position[1] + directions[key][1]]
    piece_potentielle = tetromino(piece.nom,
                                  nextposition,
                                  piece.orientation)
    # Si bas et pas collision -> la piece est changee
    if not collision(partie,piece_potentielle):
        piece = piece_potentielle
    # Si bas et collision -> la partie est changee (+hbox de la piece)
    else:               
        # Update la hitbox de la partie
        for bloc in set( piece.hitbox.keys()  ) &                            \
                    set( partie.hitbox.keys() ):
            partie.hitbox[bloc] = piece.hitbox[bloc]
        # Si ya completion de ligne -> effacage de ligne, score up  
        if completion(partie):
            effacage(ecr,partie,chrono_jeu)
        # Finalement remise de la nouvelle piece (deja determinee pour 
        # pouvoir l'afficher dans NEXT et on choisit a pouf la next d'apres)
        piece  = tetromino(partie.piece_suivante)
        partie.piece_suivante = forme_au_hasard()
        # Faut verifier si y'a la place pour celle ci sinon game over!
        if collision(partie,piece):
            return False
    return [ecr,partie,piece]

# Ajoute les caracteres d'une hitbox a l'ecran (mais ne refresh pas)
def affiche(ecr,item):
    hitbox = item.hitbox
    ## chaque "pixel" de la hitbox est de style ( (y,x) , "caractere" )
    for pixel in hitbox.keys():
        try:
            ecr.addstr(pixel[0], pixel[1],hitbox[pixel],curses.color_pair(item.couleur))
        except:
            pass

# Affiche le titre, press start clignotant en attendant un input.
def affiche_titre(ecr):
    ecr.resize(18,24)
    titre = [r'▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚','▌                    ▐',
           '▌  ┏━━━━━━━━━━┳━━━┓  ▐','▌  ┣━┳━━ ━┳━━ ╋   ┃  ▐',
            '▌  ┃ ┃ ┏━ ┃┏━┓ ┏━┓┃  ▐','▌  ┃ ┃ ┣  ┃┣┳┛┃┗━┓┃  ▐',
             '▌  ┃ ┃ ┗━ ┃┃┗━┫┗━┛┃  ▐','▌  ┗━━━━━━━━━━┻━━━┛  ▐',
              '▌                    ▐','▌                    ▐',
               '▌                    ▐','▌                    ▐',
                '▌                    ▐','▌                    ▐',
                 '▌                    ▐','▙▅▆▇█▇▆▅▆▇██▇▆▅▆▇█▇▆▅▟']
    titre2 = ['┏━━━━━━━━━━┳━━━┓','┣━┳━━ ━┳━━ ╋   ┃','┃ ┃ ┏━ ┃┏━┓ ┏━┓┃',
            '┃ ┃ ┣  ┃┣┳┛┃┗━┓┃','┃ ┃ ┗━ ┃┃┗━┫┗━┛┃','┗━━━━━━━━━━┻━━━┛']

    for i , car in enumerate(titre):
        ecr.addstr(1+i,1,car,curses.color_pair(6))
        
    for i , car in enumerate(titre2):
        ecr.addstr(3+i,4,car,curses.color_pair(8))
    ecr.border()
    ecr.addstr(12,5,'"Press Start"',curses.color_pair(6))
    ecr.refresh()
    minuteur = chronometre(0.7)
    minuteur.start()
    now = 0
    while True:
        if ecr.getch() != -1:
            break
        if now != minuteur.tictac:
            now = minuteur.tictac
            if minuteur.tictac == 0:
                ecr.addstr(12,5,'~Press Start~',curses.color_pair(6))
            else:
                ecr.addstr(12,5,'~Press Start~',curses.color_pair(9)|curses.A_REVERSE)
        ecr.refresh()
    minuteur.stop()


# Affiche un menu de pause jusqu'a nouvel input
def affiche_pause(ecr,chrono_jeu,temps_jeu):
    chrono_jeu.stop()
    temps_jeu.stop()
    ecr.nodelay(False)
    ecr.erase()
    ecr.resize(18,24)
    #titre = ['Rotation:',' v = gauche',' b = droite',' ','Deplacement:',
    #         '    ←↓→',' ','Quitter:    ','    Esc']
    titre = [r'┏━━━━━━━━━━━━━━┓','┃ Rotation:    ┃','┃  v = gauche  ┃',
               '┃  b = droite  ┃','┃              ┃','┃ Deplacement: ┃',
                '┃    ← ↓ →     ┃','┃              ┃','┃ Quitter:     ┃',
                 '┃     Esc      ┃','┗━━━━━━━━━━━━━━┛']
    for i , car in enumerate(titre):
        ecr.addstr(3+i,4,car,curses.color_pair(1))
    ecr.border()
    ecr.refresh()
    if ecr.getch():
        chrono_jeu.start()
        temps_jeu.start()
        ecr.timeout(1)
   
# Affiche le game over, attend un input pour continuer ou quitter
def affiche_game_over(ecr,partie,chrono_jeu,temps_jeu):
    chrono_jeu.stop()
    temps_jeu.stop()
    time.sleep(1)
    ecr.erase()
    ecr.resize(18,24)
    titre = ['┏━━      ┏━','┃┣┓┏┓┏┓┏┓┣ ','┗━┫┣┫┃┗┛┃┗━','┏━┳┓  ┏━┏━┓',
             '┃ ┃┗┓┏╋ ┣┳┛','┗━┛ ┗┛┗━┫┗━',' ','  '+str(partie.score)+' lignes']
    for i , car in enumerate(titre):
        ecr.addstr(3+i,6,car,curses.color_pair(3))
    ecr.border()
    ecr.refresh()
    ecr.nodelay(False)
    continuer = True
    while True:
        ecr.refresh()
        if continuer == True:
            ecr.addstr(12,8,'Rejouer')
            ecr.addstr(13,8,'Quitter',curses.color_pair(0))
        else:
            ecr.addstr(12,8,'Rejouer',curses.color_pair(0))
            ecr.addstr(13,8,'Quitter')
        key = ecr.getch()
        if key in [curses.KEY_UP,curses.KEY_DOWN,
                          curses.KEY_RIGHT,curses.KEY_LEFT]:
            continuer = not continuer
        if key not in [curses.KEY_UP,curses.KEY_DOWN,
                           curses.KEY_RIGHT,curses.KEY_LEFT]:
            if continuer:
                main(ecr)
            else:
                sys.exit()

# Refresh et affiche tout...
# issuing noutrefresh() calls on all windows, followed by a single doupdate().
def imprime(ecr,side1,side2,partie,piece,temps_jeu):
    ecr.erase()
    ecr.border()
    side1.erase()
    side1.border()
    side2.erase()
    side2.border()
    side1.addstr(0,4,'NEXT')
    # C'est pour afficher dans NEXT a [1,3]
    affiche(side1,(tetromino(partie.piece_suivante,[1,3])))
    side2.addstr(2,3,'TEMPS')
    t = str(temps_jeu.duree//60)+':'+str(temps_jeu.duree%60)
    side2.addstr(3,6,t,curses.color_pair(0))
    side2.addstr(4,3,'LIGNES')
    side2.addstr(5,6,str(partie.score),curses.color_pair(0))
    side2.addstr(6,3,'NIVEAU')
    side2.addstr(7,6,str(partie.niveau),curses.color_pair(0))
    side2.addstr(8,3,'SPEED')
    side2.addstr(9,6,str(partie.vitesse),curses.color_pair(0))
    
    affiche(ecr,partie)
    affiche(ecr,piece)
    # Au lieu de refresh 1 par 1 on actualise d'abord toutes les fenetres
    # (nourefresh) individuellement puis on affiche tout d'un coup
    # avec doupdate.
    ecr.noutrefresh()
    side1.noutrefresh()
    side2.noutrefresh()
    curses.doupdate()
   
# En cas de ligne complete on enregistre son index dans l'objet partie
def completion(partie):
    for i in range(1,partie.hauteur+1):
        # "hitbox" de la ligne examinee
        lbox = {coor: partie.hitbox[coor] for coor in partie.hitbox.keys()\
                                          if coor[0]==i}
        # si pas de blanc dans la ligne on la met dans "complete"
        if ' ' not in lbox.values():
            partie.complete.update(dict(lbox))
    return True if partie.complete else False

# Y s'en passe des trucs quand on efface des ligne...
# incremente le score, incremente le niveau (et donc la vitesse) au besoin,
# affiche la dispartion des lignes avec un bel effet de flash et finalement
# met a jour la hitbox de la partie (du terrain).
def effacage(ecr,partie,chrono_jeu):
    lignes_completes = set([y[0] for y in partie.complete.keys()])
    partie.score = partie.score + len(lignes_completes)
    # python3 divise arrondi avec //
    partie.niveau = int(partie.score//10)
    # la vitesse diminue de 0.1 par niveau (= par 10 lignes) jusqu'a 0.1
    partie.vitesse = 1-(partie.niveau/10) if partie.vitesse > 0.1 else 0.1
    chrono_jeu.tempo = partie.vitesse
    # Flash les lignes (blocs en fait) qui vont disparaitre.
    for coord in partie.complete.keys():
        ecr.addstr(coord[0],coord[1],partie.complete[coord],curses.A_REVERSE)
    ecr.refresh()
    # Sleep sinon on a pas le temps de voir le flash
    time.sleep(0.1)
    for coord in partie.complete.keys():
        ecr.addstr(coord[0],coord[1],partie.complete[coord])
    ecr.refresh()
    time.sleep(0.1)
    for coord in partie.complete.keys():
        ecr.addstr(coord[0],coord[1],partie.complete[coord],curses.A_REVERSE)
    ecr.refresh()
    time.sleep(0.1)
    # Efface les blocs (pas necessaire mais pour le visuel)
    for bloc in set( partie.complete.keys() ) &                               \
                set( partie.hitbox.keys() ):
        partie.hitbox[bloc] = ' '
    ecr.refresh()
    time.sleep(0.1)
    # Tassage des lignes: on fait chaque ligne de bas en haut et si la
    # ligne est vide on la passe sinon on la copie dans une 2eme hitbox
    # de etat_partie. L'index de la 2eme partie augmente seulement
    # en cas de copiage.
    partie_temp = etat_partie()
    y_temp = partie_temp.hauteur-1
    # Rappel: en "haut" y = 0 et en bas y = "etat_partie.hauteur"
    for y in range(partie.hauteur-1,0,-1):
        # on fait un set avec les car de la ligne est si il est egal a
        # (' ') alors c'est une ligne vide.
        set_ligne = {partie.hitbox[coord] for coord in partie.hitbox.keys()
                                                    if coord[0] == y }
        # Si la ligne est pas vide on la copie et on "monte d'un cran"   
        # Rm: les sets c'est () normalement mais en set comprehension
        # ca devient {} ... pas genial ou alors pas capte l'astuce.
        if set_ligne != {' '}:
            for coord in [c for c in partie.hitbox.keys() if c[0] == y]:
                partie_temp.hitbox[(y_temp,coord[1])] = partie.hitbox[coord]
            y_temp = y_temp - 1
    partie.hitbox = partie_temp.hitbox   
    # Remet "complete" (contenant les blocs a effacer) a zero.
    partie.complete.clear()

# MAIN
######
# Le wrapper commence avec ecr comme fenetre standard de la taille du terminal.
def main(ecr):
    ecr.nodelay(True)
    curses.curs_set(False)             # (pas de curseur clignotant)
    #curses.use_default_colors()        # (utilise le setup initial du terminal)

    curses.init_pair(1, curses.COLOR_BLACK   , curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_WHITE   , curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED     , curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLUE    , curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_GREEN   , curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN    , curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_MAGENTA , curses.COLOR_BLACK)
    curses.init_pair(8, curses.COLOR_YELLOW  , curses.COLOR_BLACK)
    curses.init_pair(9, curses.COLOR_YELLOW  , curses.COLOR_CYAN)

    # Initialisation du Jeu:
    # - la partie (ecr principal avec hitbox)
    # - une 1ere piece (faudrait une 2 eme a display dans next)
    # - le chrono (classhread qui regle la vitesse de la descente des pieces)
    # - un 2eme chrono pour le temps de jeu (invariable)
    partie = etat_partie()
    piece  = tetromino(forme_au_hasard())
    chrono_jeu = chronometre(partie.vitesse)
    temps_jeu = chronometre(1)
    maintenant = 0
   
    # Ecran titre (attend une entree avant de passer a la suite). On erase 
    # d'abord au cas ou vienne d'un continue et qu'il y ait des restes
    ecr.erase()
    ecr.attron(curses.color_pair(1))
    affiche_titre(ecr)
       
    # Initialise les fenetres suivant les proportions du tetris originel.
    # Rm: curses.newwin(nbre_lines, nbre_cols, begin_y, begin_x)
    ecr.resize(partie.hauteur+1,partie.largeur+1)
    side1 = curses.newwin(6,12,0,12)
    side2 = curses.newwin(12,12,6,12)
    side1.attron(curses.color_pair(1))
    side2.attron(curses.color_pair(1))
    side1.erase()
    side2.erase()

    # Afffiche l'ecran de jeu
    imprime(ecr,side1,side2,partie,piece,temps_jeu)
   
    # La boucle principale qui fait tourner le jeu proprement dit.
    chrono_jeu.start()
    temps_jeu.start()
    while (True):
        # Prend la commande entree par le joueur
        key = ecr.getch()

        # Descente a chaque fois que le chrono change
        if maintenant != chrono_jeu.tictac:
            # on remet maintenant a la meme valeur que le tictac -> on entrera
            # plus dans cette boucle jusqu'au prochain changement de tictac.
            maintenant  = chrono_jeu.tictac
            try:
                ecr,partie,piece = descente(ecr,partie,piece,chrono_jeu)
            except:
                affiche_game_over(ecr,partie,chrono_jeu,temps_jeu)
       
        # Quitte la partie.
        if key == 27:
            # Faut stopper les chronothreads sinon ca continue de son cote.
            chrono_jeu.stop()
            temps_jeu.stop()                                                  
            break

        # Pause la partie si on appuie sur un caractere autre que b,v,B,V
        if key in set(range(32 , 127)) - {66,98,118,86}:
            affiche_pause(ecr,chrono_jeu,temps_jeu)
            # Une fois sorti de la pause on reaffiche le jeu correctement
            ecr.resize(partie.hauteur+1,partie.largeur+1)
            imprime(ecr,side1,side2,partie,piece,temps_jeu)
       
        if key == curses.KEY_DOWN:
            try:
                ecr,partie,piece = descente(ecr,partie,piece,chrono_jeu)
            except:
                affiche_game_over(ecr,partie,chrono_jeu,temps_jeu)
       
        # si gauche droite on tente de bouger et si collision status quo
        if key == curses.KEY_LEFT or key == curses.KEY_RIGHT:
           
            nextposition = [piece.position[0] + directions[key][0] ,
                            piece.position[1] + directions[key][1]]
            #ecr.getch() ############################ <- PQ Y A CA ICI?????

            piece_potentielle = tetromino(piece.nom,
                                          nextposition,
                                          piece.orientation)
            if not collision(partie,piece_potentielle):
                piece = piece_potentielle
       
        ## pivote a droite:
        if key == 66 or key == 98:
            piece_potentielle = tetromino(piece.nom,
                                          piece.position,
                                          piece.orientation+1)
            if not collision(partie,piece_potentielle):
                piece = piece_potentielle
        # pivote a gauche:
        if key == 118 or key == 86:
            piece_potentielle = tetromino(piece.nom,
                                          piece.position,
                                          piece.orientation-1)
            if not collision(partie,piece_potentielle):
                piece = piece_potentielle
       
        # On a tout passe en revue: on affiche la nouvelle situation!
        imprime(ecr,side1,side2,partie,piece,temps_jeu)

# Tout commence ici avec le redimensionnement du terminal:
# Subprocess est mieux car capte les msg d'erreurs mais ne marche pas partout.
# Donc si ca fail on tente os.system, present partout mais pas try-catchable.
try:
     ## 5 -> "gravity" = center. Cad repositionnement par rapport au centre. 
     ## -1 -1 sont les coord x,y de depart et 200,280 les nouvelles dimensions
    subprocess.call('wmctrl -r :ACTIVE: -e 5,-1,-1,200,280')
except:
    print('\nImpossible de redimensioner le terminal.\nFaites le vous meme svp.\nLa taille est 24x18')
    time.sleep(3)
    os.system('wmctrl -r :ACTIVE: -e 5,-1,-1,200,280')
# Un wrapper deja tout fait qui garanti une sortie propre de curse
# en cas de merdouille.
curses.wrapper(main)


# TRUCS DIVERS #
#
###############
# Game Engine #
###############

# Texture Pack : 
# ░ ▒ ▓ █

# Sprite Library: 
# ▀ ▁ ▂ ▃ ▄ ▅ ▆ ▇ █ ▉ ▊ ▋ ▌ ▍ ▎ ▏ ▐ ▔ ▕ ▖ ▘ ▙ ▚ ▛ ▜ ▝ ▞ ▟

# Interface Design :
#┏ ━ ┓┃┗ ┛┻ ┫┣ ┳ ╋

# ASCII Code :
# 27 = ESC
# 81,113 = Q,q
# 66,98  = B,b
# 86,118 = V,v
#

# Decoration :
#┏━━━━━━━━━━━━┳━━━━━━━━━━┓
#┃            ┃  TETRIS  ┃
#┃           
#┃            ┃          ┃
#┃            ┃SCORE:    ┃
#┃            ┣━━━━━━━━━━┫
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃ 
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃
#┃            ┃          ┃
#┗━━━━━━━━━━━━┻━━━━━━━━━━┛

#            ▁
#▞▔▂ ▞▚ ▐▚▞▌▞▁
#▚▄▞▞▔▔▚▐  ▌▚▁
#        ▁
#▞▀▚▚  ▞▞▁▐▔▟
#▚▄▞ ▚▞ ▚▁▐▔▚


#▊
#▊
#▊

#▄▙▖

#▟▖

#▄█▄

#▀▀█▀▀
#  █
#  █
#▐▛▀▀
#▐▙▄
#▐▌
#▝▀▀▀

#┏━━━━━━━━━━━━┳━━━━━━━━━┓
#┃                      ┃
#┃      HIGH SCORES     ┫
#┃      ___________     ┃
#┃                      ┃
#┃   1st  SNK   20000   ┃
#┃   2nd  OLI   17500   ┃
#┃   3rd  BEN   15000   ┃
#┃   4th  PIT   12500   ┃
#┃   5th  CAP   10000   ┃ 
#┃   6th  SAM    7500   ┃
#┃   7th  KON    5000   ┃
#┃   8th  TAI    2500   ┃
#┃   9th  MAR       1   ┃
#┃                      ┃
#┃                      ┃
#┃                      ┃
#┗━━━━━━━━━━━━┻━━━━━━━━━┛

#┌──────────────────────┐
#│▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚▞▚│
#│▌                    ▐│
#│▌  ┏━━━━━━━━━━┳━━━┓  ▐│
#│▌  ┣━┳━━ ━┳━━ ╋   ┃  ▐│
#│▌  ┃ ┃ ┏━ ┃┏━┓ ┏━┓┃  ▐│
#│▌  ┃ ┃ ┣  ┃┣┳┛┃┗━┓┃  ▐│
#│▌  ┃ ┃ ┗━ ┃┃┗━┫┗━┛┃  ▐│
#│▌  ┗━━━━━━━━━━┻━━━┛  ▐│
#│▌                    ▐│
#│▌                    ▐│
#│▌                    ▐│
#│▌                    ▐│
#│▌   "Press Start"    ▐│
#│▌                    ▐│
#│▌                    ▐│
#│▙▅▆▇█▇▆▅▆▇██▇▆▅▆▇█▇▆▅▟│
#└──────────────────────┘


