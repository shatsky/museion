**Что это такое?**

Музыкальная библиотека, работающая на [специально разрабатываемой](https://github.com/shatsky/djmuslib) [системе управления контентом](http://ru.wikipedia.org/wiki/%D0%A1%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0_%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F_%D1%81%D0%BE%D0%B4%D0%B5%D1%80%D0%B6%D0%B8%D0%BC%D1%8B%D0%BC) и наполненная контентом с сайта [ККРЭ](http://kkre-1.narod.ru/)

**Зачем это нужно? Есть куча музыки вконтакте.**

Всего хорошего.

**Зачем это нужно? Ведь на [http://kkre-1.narod.ru/](http://kkre-1.narod.ru/) есть все то же самое.**

ККРЭ наполняется редактированием вручную статических страниц. Это крайне неудобно, приводит к неконсистентности (например, разные описания одной и той же записи на разных страницах, отсутствие аудиозаписи в списке на странице композитора, упомянутого в ее описании на странице исполнителя, или вообще отсутствие страницы со списком творчества человека, упоминаемого в описаниях аудиозаписей на существующих страницах), не позволяет менять формат и оформление списков и т. д. Собственно, проект начат из желания улучшить ККРЭ, первичная цель - сделать для нее нормальную систему управления контентом с реляционной базой и шаблонами. Мы также пытаемся автоматизировать преобразование их списков в базу - почти весь имеющийся здесь контент импортирован автоматически.

**Зачем это нужно? Есть же модули организации музыки для существущих CMS.**

Практически все существующие решения имеют простейшую схему "исполнитель - альбом - трек", совершенно неприемлемую для нас по многим причинам. В частности, ввиду специфики музыки, на которую мы ориентируемся, в нашем случае поэты и композиторы не менее важны, чем исполнители. В общем, нам нужна более высокая детализация и более сложная схема базы, подходящих готовых решений нет.

**Зачем это нужно? Есть же OpenWiki.**

OpenWiki предназначена для решения совершенно других задач. Основным объектом вики является статья, связью - ссылка на другую статью. У нас же объекты - люди, произведения, исполнения, связи - принадлежность авторства, исполнения и т. д. Задачу автоматического построения списков произведений и записей по этим связям вики никак не решает.

**Почему тут одна советская музыка?**

См. ответ на первый вопрос.

**Да кому вообще нужна советская музыка!?**

См. ответ на второй вопрос.

**И что, ничего, кроме советской музыки, здесь не будет?**

Пока что это просто развернутый прототип для демонстрации возможностей CMS применительно к контенту ККРЭ. Если она будет доведена до пригодного к продакшену состояния и организаторы ККРЭ станут ее использовать - возможно, здесь вообще ничего не будет. Если я все же решу расширять получившуюся здесь базу независимо от ККРЭ - может, и будет. Хотя, на мой взгляд, из всей музыки, которую я нахожу хорошей, советской наиболее всего угрожает незаслуженное забвение.

**А что с авторскими правами на аудиозаписи?**

Для аудиозаписей из ККРЭ - то же самое, что и у ККРЭ. См. предпоследний абзац на их главной странице.

**Зачем кнопку проигрывания и исполнителя выносить на отдельную строку?**

Аудиозаписи сгруппированы по произведениям. Произведение - комбинация определенных текста и музыки. Под строкой произведения (название, поэт, композитор) может находиться множество его исполнений, каждое отображается на отдельной строке. В том числе если оно единственное для данного произведения.

**Почему списки выглядят так аскетично? У меня есть отличная идея, как их разукрасить.**

Предлагайте свои отличные идеи, только сперва обдумайте, как это будет выглядеть на всевозможных вариантах (список с преимущественно единственным исполнением каждого произведения, с множеством исполнений, с одним и тем же исполнителем, с разными, ...). Скорее всего, в результате вы решите ничего не предлагать.

**Для начала нужно сделать так, чтобы поля списка имели фиксированную ширину!**

Для того, чтобы сделать это правильно, нужна статистика длин строк в этих полях с учетом используемых шрифтов. Пока что есть более первостепенные задачи.

**Почему бы не убрать имя человека, которому посвящена страница, из описаний в выводимом на ней списке? И так же понятно.**

Не всегда понятно. Для некоторых записей человек, известный как композитор, может быть и исполнителем. Для некоторых записей исполнитель может быть одним из нескольких соисполнителей. Да, можно выделить отдельный блок "в исполнении автора", можно указывать "вместе с"... Но таких тонкостей много, и учитывать их все в генераторе списков мне пока что не кажется целесообразным.

**Почему бы не добавить на страницах людей строку пути, что-то вроде "Поэты > С > Константин Симонов"?**

Потому что это не имеет смысла. Многие люди совмещали несколько видов деятельности и, соответственно, отображаются в нескольких категориях.

**Что означает название Djmuslib?**

Django Music Library - технически система выполнена в виде приложения для фреймворка Django.