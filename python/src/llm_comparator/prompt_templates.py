# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Prompt templates for the LLM Comparator script."""

COHERENT_JUDGE = """
### **Prompt del Giudice LLM con Attività di Tagging**

**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q) e un ragionamento (R). Il tuo compito è determinare se la risposta A è coerente con la domanda Q, tenendo conto del ragionamento R.

---

**Procedura di Valutazione**

1. **Analisi della Domanda (Q):**
   - Identifica chiaramente l'intento principale di Q.
   - Determina quali informazioni specifiche vengono richieste.

2. **Esame della Risposta (A):**
   - Valuta se A affronta direttamente l'intento principale di Q.
   - Verifica che A non confonda concetti correlati ma distinti.
   - Controlla se A è coerente con il contesto di Q.

3. **Esame del Ragionamento (R):**
   - Se il ragionamento R è "N/A" non va considerato. 
   - Valuta se R dimostra una comprensione corretta della domanda Q.
   - Conferma che R non introduce errori o confusioni su concetti correlati ma distinti.
   - Assicurati che R supporti adeguatamente la risposta A.

4. **Valutazione Finale:**
   - Se A è coerente con Q e R conferma una comprensione corretta di Q, il verdetto è `Coerente`.
   - Se A sembra inerente a Q ma R mostra una mancata comprensione di Q, il verdetto è `Wrong`.
   - Se A non è coerente con Q, indipendentemente da R, il verdetto è `Wrong`.
   - Se A è coerente con Q e R è "N/A" il verdetto è 'Coerente'.

---

**Regole di Valutazione**

1. **Coerenza tra A e Q:**
   - Non è necessario che A sia 'corretta' per essere considerata coerente. Deve semplicemente affrontare l'intento principale di Q.
   - A deve essere pertinente al contesto di Q e non confondere concetti correlati ma distinti.
   - La risposta A può contenere identificativi di nomi e cognomi anonimizzati come RICHIEDENTE_*** o GIUDICE_*** etc. 

2. **Ruolo del Ragionamento (R):**
   - R serve a corroborare A e dimostrare la comprensione della domanda Q.
   - Se R è incoerente o mostra una mancata comprensione di Q, anche una risposta apparentemente corretta A deve essere valutata come `Wrong`.

---

**Formato di Output**

Presenta la tua valutazione nel seguente formato XML:

```xml
<result>
  <explanation>LA TUA SPIEGAZIONE QUI.</explanation>
  <verdict>UNO DEI VERDETTI QUI.</verdict>
</result>
```

**Opzioni di Verdetto:**
- `Coerente`: La risposta A è coerente con la domanda Q e il ragionamento R conferma una comprensione corretta di Q.
- `Wrong`: La risposta A non è coerente con la domanda Q oppure il ragionamento R mostra una mancata comprensione di Q.

---

**Esempi**

**Esempio 1:**
- **Q:** Come si chiama il primo imperatore romano?
- **A:** Marco Aurelio
- **R:** L'imperatore romano Marco Aurelio è conosciuto come il saggio.

**Analisi:**
- La domanda Q chiede il nome di una persona. La risposta A fornisce un nome, quindi è inerente.
- Il ragionamento R mostra una comprensione della domanda.

```xml
<result>
  <explanation>A è inerente a Q, e R mostra comprensione della domanda.</explanation>
  <verdict>Coerente</verdict>
</result>
```

**Esempio 2:**
- **Q:** Come si chiama il primo imperatore romano?
- **A:** Giulio.
- **R:** Il postino si chiamava Giulio.

**Analisi:**
- La domanda Q chiede il nome di una persona. La risposta A fornisce un nome, quindi è inerente.
- Tuttavia, il ragionamento R è completamente fuori contesto e mostra una mancata comprensione della domanda.

```xml
<result>
  <explanation>A sembra inerente a Q, ma R mostra una mancata comprensione della domanda.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 3:**
- **Q:** Come si chiama il primo imperatore romano?
- **A:** Fino alla quarta elementare.
- **R:** Ho insegnato storia a Marco fino alla quarta elementare.

**Analisi:**
- La domanda Q chiede il nome di una persona. La risposta A non fornisce un nome e parla invece di un periodo di tempo, quindi non è coerente con Q.
- Il ragionamento R è completamente fuori contesto.

```xml
<result>
  <explanation>A non è coerente con Q.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 4:**
- **Q:** A Francesco piace il gelato al cioccolato (SI, NO, N/A)?
- **A:** NO
- **R:** Plutone non è più un pianeta dal 2006, l'Unione Astronomica Internazionale, ha deciso di “declassare” Plutone a Pianeta Nano.  

**Analisi:**
- La domanda Q chiede se a Francesco piace il gelato al cioccolato e si aspetta una risposta SI, NO, N/A. La risposta A (NO) è nel fromato corretto.
- Il ragionamento R è completamente fuori contesto, parla di Plutone e del suo status di pianeta. 

```xml
<result>
  <explanation>A non è coerente con Q.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 5:**
- **Q:** Francesco Ha rettificato il suo nome rispetto a quanto dichiarato nel documento C3? (SI, NO, N/A)?
- **A:** SI 
- **R:** Nome: Francesco.  

**Analisi:**
- La domanda Q chiede se ha rettificato il suo nome e si aspetta una risposta SI, NO, N/A. La risposta A (NO) è nel fromato corretto.
- Il ragionamento R capisce che la domanda riguarda il nome. 

```xml
<result>
  <explanation>A  è coerente con Q.</explanation>
  <verdict>Coerente</verdict>
</result>
```

---

**Il Tuo Compito:**
Valuta la seguente Q, A, R secondo le regole sopra indicate. Fornisci il tuo output nel formato XML specificato.

- **Q:** {prompt}
- **A:** {response_a}
- **R:** {text_reference}

**Nota finale:**
- Sii obiettivo e limitati alle informazioni fornite. Non fare inferenze o assunzioni aggiuntive.
- Concentrati sulla coerenza tra A e Q, e sul ruolo di R nel dimostrare la comprensione della domanda.
"""

RECURSIVE_JUDGE = """
### **Prompt del Giudice LLM con Attività di Tagging**

**Input**
RT: {full_text}
Q: {prompt}
A: {response_a}
GTA: {response_b}
MR: {model_reasoning}


**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q), una risposta di riferimento (GTA) e il testo (RT) usato per formulare la risposta.
Utilizza ragionamento modello (MR) per verificare se le informazioni aggiunte in A' sono supportate da RT. 
Se il verdetto è etichettato come **Hallucination** o **Inference**, allora dovresti controllare il ragionamento del modello (MR). In questa condizione, se il testo MR **non è contenuto** in RT, il verdetto corrispondente dovrebbe essere etichettato come **Hallucination**. Altrimenti, il verdetto dovrebbe essere **Inference** quando il testo MR è validamente dedotto dal testo RT.
Ad ogni riposta possono corrispondere più verdetti, ma a una singola parte può essere assegnato un singolo verdetto.

---

**Procedura di valutazione**

- Passo 0. Analizzare la risposta di riferimento GTA:
-- riposta la risposta di riferimento GTA esattamente come ti è stata fornita
-- non cambiare la risposta di riferimento GTA
-- anche se la risposta di riferimento GTA è "N/A" non cercare una risposta nel testo
-- se possibile scomponi la risposta di riferimento GTA in parti GTA'

- Passo 1. Analizzare la Domanda Q:
- - Se la domanda Q ha una struttura condizionale ("Se..., quale/perché/chi/come/dove"):
- - - Non considerare la parte condizionale ("Se...") come una sottodomanda separata
- - - Trattala come contesto per la domanda principale
- - valutare quali informazioni specifiche vengono richieste dalle parti. 


- Passo 2. Esaminare la Risposta A:
- - Se la risposta A è complessa, dividerla in parti più semplici (A → A') per facilitare la comprensione
- - - Nota: non considerare la risposta alla parte condizionale ("Se..") della domanda Q descritta in Passo 1. come una risposta separata. 
- - valuta se le singole parti A' di A forniscono una risposta alla domanda Q
- - Verifica se la risposta A è una parafrasi di N/A ad es: "nel documento non ci sono riferimenti a..". Se è una parafrasi segnalalo e considera la risposta A come N/A per l'analisi successiva.
- - Verifica se A o una parte A' corrisponde in significato alla risposta di riferimento GTA.
- - Verifica se A tralascia informazioni contenute nella risposta di riferimento GTA. 

- Passo 3. Analizza il Testo di Riferimento RT:
- - Verificare se A o una parte A' introduce nuove informazioni non presenti nel testo di riferimento RT.
- - Identificare se RT contiene informazioni esplicite o implicite che supportano A'.
- - - Se implicite, determinare se le premesse contenute in RT sono valide e implicano A'.

- Passo 4: Applicazione delle Regole di Valutazione:
- - Applica le seguenti regole per assegnare il verdetto a ciascuna parte A'.

- Passo 5: Valutazione del Model Reasoning (MR) e il Verdetto:
  - Se il verdetto è etichettato come **Hallucination** o **Inference**, considera MR, il ragionamento usato dal modello per formulare A.  
  - Se MR **non è contenuto** in RT, l'informazione aggiunta in A' è considerata **Hallucination**.  
  - Se MR **è presente** in RT, l'informazione aggiunta in A' è dedotta validamente e viene etichettata come **Inference**.

---

**Regole di Valutazione:**
Con A' si intende una parte di A, una domanda A può avere più valutazioni, ma ogni parte A' può avere un singolo label. 

1. **A' e GTA corrispondono perfettamente nel significato (possono essere formulate diversamente):**
   Verdetto: `Correct`
   Spiegazione: Spiega perché A' e GTA corrispondono nel significato.

2. **A' e GTA sono diversi:**
   Verdetto: `Wrong`
   Spiegazione: Spiega perché A' e GTA differiscono.

3. **A fornisce una risposta incompleta:**
   Verdetto: `Incomplete`
   Spiegazione: Spiega quali parti di della risposta di riferimento mancano per rendere A completa.  

4. **A' aggiunge informazioni rispetto a GTA che può essere inferta da RT:**
   Verdetto: `Inference`
   Spiegazione: Spiega quali informazioni aggiunge A' rispetto a GTA, indicando le premesse in RT che le supportano e confermate da MR. Perché A' sia considerata 'Inference' l'inferenza deve essere valida. Ovvero le premesse devono implicare la conclusione. 

5. **A' aggiunge informazioni non presenti nel teso di riferimento RT.**  
   Verdetto: `Hallucination`  
   Spiegazione: Indica che A' fornisce una risposta che non ha riscontro in RT nè in modo esplicito, nè attraverso inferenza, in quanto MR non risulta supportato dal testo (RT). A' differenza di un `Inference` l'informazione (o il ragionamento del modello (MR)) non può essere inferta dal testo (RT).  

6. **A' e GTA sono entrambi N/A:**
   Verdetto: `True Negative`
   Spiegazione: Indica che sia A' che GTA sono N/A.

7. **A' è N/A mentre GTA contiene una risposta:**
   Verdetto: `Missing Answer`
   Spiegazione: Indica che A' è mancante mentre GTA fornisce una risposta.

---

**Linea Guida per Differenziare Inference e Hallucination:**
- **Pertinenza alla Domanda:** 
- - Se l'informazione in A' non è presente nel testo A' è **Hallucination**.
- - Se l'informazione in A' è dedotta da RT e le premesse implicano la conclusione **Inference**.

- **Utilizzo del Model Reasoning (MR):**  
- - Verifica se il testo MR è presente in RT:  
- - - Se **MR non è presente** in RT, l'informazione aggiunta in A' è considerata **Hallucination**.  
- - - Se **MR è contenuto** in RT, l'informazione è considerata **Inference**.


**Line Guida per differenziare fra inferenza valida e inferenza non valida**
- Le premesse presenti in RT implicano A'? Per capirlo bisogna valutare se le premesse sono valide per inferire A'.
- - Se le premesse sono valide A' è **Inference**.
- - Se le premesse non sono valide A' è **Wrong**.

---

**Opzioni di Verdetto:**
Il verdetto deve essere uno dei seguenti:
['Correct', 'Wrong', 'Incomplete', 'Inference', 'Hallucination', 'Missing Answer', 'True Negative']


**Formato di Output:**
Presenta la tua valutazione nel seguente formato XML:

Analisi:
ANALISI A PASSI QUA

```xml
<result>
  <explanation>LA TUA SPIEGAZIONE PER OGNI VERDETTO QUI.</explanation>
  <verdict>I VERDETTI SELEZIONATI QUI.</verdict>
</result>
```

---

**Esempi:**

**Esempio 1:**
Q: Che lavoro faceva il richiedente?
A: Cuoco
GTA: cuoco
RT: Mario lavora come cuoco da 5 anni presso la cooperativa sociale. Ha una moglie e due figli che vanno a scuola. 
MR: lavora come cuoco da 5 anni

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "cuoco", afferma che il lavoro è cuoco.

- Passo 1:
La domanda riguarda il lavoro svolto dal richiedente.

- Passo 2:
La risposta corrisponde a GTA. 
La risposta non tralascia informazioni presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito la risposta (lavora come cuoco). 

- Passo 4: 
Applicando le regole risulta che la risposta A corrisponde a GTA, non tralascia informazioni ed è esplicitamente presente nel testo. Perciò è 'Correct'.  

- Passo 5:
Il verdetto è etichettato come **Hallucination** o **Inference**. 

```xml
<result>
  <explanation>A e GTA hanno lo stesso significato.</explanation>
  <verdict>Correct</verdict>
</result>
```

**Esempio 2:**
Q: Che lingue parla il richiedente?
A: Francese, Tedesco
GTA: Francese
RT: Il richiedente è di madrelingua francese passa spesso le vacanze in Germania. 
MR: madrelingua francese passa spesso le vacanze in Germania

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "Francese", afferma che la lingua parlata è Francese.

- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese ed Tedesco.
La parte di risposta (Francese) corrisponde a GTA. 
La risposta non tralascia informazioni presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito parte della risposta (madrelingua francese). 
La risposta (Tedesco) introduce un inferenza non valida, nel testo RT si menziona che il richiedente va in vacanza in germania. Questo premessa non è valida per inferire che il richiedente parli tedesco.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese corrisponde a GTA, mentre la parte di risposta Tedesco è un inferenza non valida. Anche se MR è incluso nel testo RT, questo è considerato come inferenza non valida nel passo 3 perche premessa non è valida per inferire che il richiedente parli tedesco. Quindi non abbiamo bisogno di controllare se MR è in RT o meno. Perciò è 'Correct' e 'Wrong'.

- Passo 5:
Il verdetto è etichettato come **Hallucination** o **Inference**. 

```xml
<result>
  <explanation> Francese è Correct, Tedesco è Wrong</explanation>
  <verdict>Correct, Wrong</verdict>
</result>
```

**Esempio 3:**
Q: Che lingue parla il richiedente?
A: Francese, Tedesco
GTA: Francese, Italiano
RT: Il richiedente è di madrelingua francese e vive in Germania. 
MR: madrelingua francese e vive in Germania

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "Francese, Italiano", afferma che le linguee parlate sono Francese e Italiano.

- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese ed Tedesco.
La parte di risposta (Francese) corrisponde a GTA. 
La risposta tralascia informazioni (Italiano) presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito parte della risposta (madrelingua francese). 
La risposta (Tedesco) introduce un inferenza valida, nel testo RT si menziona che il richiedente vive in germania. Questo premessa è valida per inferire che il richiedente parlai tedesco.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese corrisponde a GTA, la parte di risposta Tedesco è un inferenza valida. MR è incluso nel testo RT, e anche questo è considerato come inferenza valida nel passo 3 perche premessa è valida per inferire che il richiedente parli tedesco. Mentre Italiano viene tralasciato. Perciò è 'Correct' e 'Inference' e 'Incomplete'.

- Passo 5:
Parte del verdetto è etichettato come **Inference**, quindi considerando MR. Poiché MR è parte di RT o MR può essere inferito da RT, il verdetto selezionato 'Inferenza'.

```xml
<result>
 <explanation> Francese è Correct, Tedesco è Inference, Italiano manca quindi Incomplete</explanation>
<verdict>Correct, Inference, Incomplete</verdict>
</result>
```

**Esempio 4:**
Q: Che lingue parla il richiedente?
A: Francese, Spagnolo
GTA: Francese, Italiano
RT: Il richiedente è di madrelingua francese e vive in Germania. 
MR: madrelingua francese 

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "Francese, Italiano", afferma che le linguee parlate sono Francese e Italiano.

- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese, Spagnolo
La parte di risposta (Francese) corrisponde a GTA. 

- Passo 3:
Il testo contine in modo esplicito parte della risposta (madrelingua francese). 
La risposta (Spagnolo) non è presente nel testo RT in maniera implicita o esplicita. Risulta quini inventata.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese corrisponde a GTA, la parte di risposta Spagnolo è un hallucination perche non c'è niente in MR or RT sullo Spagnolo.  Perciò è 'Correct' e 'Hallucination' e 'Incomplete'.

- Passo 5:
Parte del verdetto è etichettato come **Hallucination**, quindi considerando MR. Poiché MR non è parte di RT o MR non può essere inferito da RT, il verdetto selezionato 'Hallucination'.

```xml
<result>
<explanation> Francese è Correct, Spagnolo è Hallucination, Italiano manca quindi Incomplete</explanation>
<verdict>Correct, Hallucination, Incomplete</verdict>
</result>
```

**Esempio 5:**
Q: Che lingue parla il richiedente?
A: Francese
GTA: N/A
RT: Il richiedente lavora come cuoco ed è venuto in italia attraverso la frontiera di Palermo.
MR: N/A

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "N/A", afferma che la risposta è "N/A", non è contenuta nel testo

- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese.

- Passo 3:
Il testo non contiene infromazioni implicite o esplicite riguardo la domanda.  
La risposta (Francese) non è presente nel testo RT in maniera implicita o esplicita. Risulta quindi inventata.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese è un hallucination, e poi MR non è presente in RT. Perciò è 'Hallucination'.

- Passo 5:
Parte del verdetto è etichettato come **Hallucination**, quindi considerando MR. Poiché MR non è parte di RT o MR non può essere inferito da RT, il verdetto selezionato 'Hallucination'.

```xml
<result>
<explanation> Francese è Hallucination</explanation>
<verdict>Hallucination</verdict>
</result>
```

**Esempio 6:**
Q: Il richiedente parla lo spagnolo (SI, NO, N/A)?
A: NO
GTA: N/A
RT: Il richiedente lavora come cuoco e gli piace arrampicare.
MR: N/A

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "N/A", afferma che la risposta è "N/A", non è contenuta nel testo

- Passo 1:
La domanda riguarda la lingue parlate dal richiedente ed vuole una risposta nel formato SI, NO, N/A.

- Passo 2:
La risposta si può scomporre in NO.

- Passo 3:
Il testo non contiene infromazioni implicite o esplicite riguardo la domanda.  
La risposta NO non è presente nel testo RT in maniera implicita o esplicita. Risulta quindi inventata.

- Passo 4: 
Applicando le regole risulta che la parte di risposta NO è un hallucination, e poi MR non è presente in RT. Perciò è 'Hallucination'.

- Passo 5:
Parte del verdetto è etichettato come **Hallucination**, quindi considerando MR. Poiché MR non è parte di RT o MR non può essere inferito da RT, il verdetto selezionato 'Hallucination'.

```xml
<result>
<explanation> NO è Hallucination</explanation>
<verdict>Hallucination</verdict>
</result>
```

**Esempio 7:**
Q: Il richiedente parla lo spagnolo (SI, NO, N/A)?
A: SI
GTA: N/A
RT: Il richiedente vive in Spagna. E gli piace il gelato alla frutta. 
MR: vive in Spagna

Analisi:

- Passo 0: 
- La risposta di riferimento GTA è: "N/A", afferma che la risposta è "N/A", non è contenuta nel testo

- Passo 1:
La domanda riguarda la lingue parlate dal richiedente ed vuole una risposta nel formato SI, NO, N/A.

- Passo 2:
La risposta si può scomporre in SI.

- Passo 3:
Il testo contiene infromazioni implicite riguardo la domanda.  
La risposta SI introduce un inferenza valida, nel testo RT si menziona che il richiedente vive in Spagna. Questo premessa è valida per inferire che il richiedente parlai spagnolo.

- Passo 4: 
Applicando le regole risulta che la parte di risposta SI è un inferenza, perche la risposta è pertinente alla domanda e MR è presente in RT. Perciò è 'Inference'.

- Passo 5:
Parte del verdetto è etichettato come **Inference**, quindi considerando MR. Poiché MR è parte di RT o MR può essere inferito da RT, il verdetto selezionato 'Inference'.

```xml
<result>
<explanation> Si è Inference</explanation>
<verdict>Inference</verdict>
</result>

---

**Note**
Presenta la tua valutazione nel seguente formato analisi + XML:

Analisi:
ANALISI A PASSI QUA

```xml
<result>
  <explanation>LA TUA SPIEGAZIONE PER OGNI VERDETTO QUI.</explanation>
  <verdict>I VERDETTI SELEZIONATI QUI.</verdict>
</result>
```


"""

