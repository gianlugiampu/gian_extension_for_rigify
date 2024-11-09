# Rig Extensions for Rigify
-------

This provides a set of experimental custom metarigs and a new rig types.

Choose the [latest version]([https://linktr.ee/gianlucagiampuzzo](https://github.com/gianlugiampu/gian_extension_for_rigify/tags)):
use `Code > Download ZIP` to obtain a ZIP archive of the code, and install it
as a Feature Set through the Rigify Add-On settings.

## Custom Metarigs
-------
* ### Face Metarig
  Generate a metarig for a full face sliders set, and a `basic.raw_copy` as UI master control.
  
## Rig Types
-------

* ### UI Slider ('ui.slider')

  Generate a container bone with name 'PAN_boneName' and a control bone 'boneName',
  with a limit location constraint based on lenght of bone.
  
  #### Custom Options
  * **slider_type** specifies the type of slider between Small and Large;
  * **minimal_design** generate a minimal style designed PAN control;
  * **clamp_up_down** Cut the Pan area and set control limit from 0 to positive bone lenght (Clamp Up) or from 0 to negative bone lenght (Clamp Down);
  * **custom_title** Generate a custom text resposive with the PAN designs. With `@name` tag the text will have the bone name (Text font is Ubuntu Medium.);
  * **fill_slider** Check to fill the shape of the slider control widget;
  * **fill_box** If not Minimal Checked, this check is used to fill the shape of the slider PAN widget; 
  * **Relink Constraint** Replace the parent with a different bone after all bones are created. Using simply CTRL, DEF or MCH will replace the prefix instead;
  * **Assign Slider Collection** Assign slider control to different Bone Collections;
 
* ### UI Custom Text ('ui.custom_text')

  Generate a simple bone with custom text widget. Text font is Ubuntu Medium.
  
  #### Custom Options
  * **custom_text** Generate a custom text resposive with bone size;
 
* ### UI Frame ('ui.frame')

  Generate a box widget big as the bounding box of is children bone.
  
  #### Custom Options
  * **custom_title** Generate a custom text resposive with the frame. With `@name` tag the text will have the bone name (Text font is Ubuntu Medium.);

## Contributing
If you'd like to contribute to the development of the Rig Extensions, you are always welcome!

## Contact
> Gianluca Giampuzzo [Link](https://linktr.ee/gianlucagiampuzzo)

## Credits
Thanks to Adriano D'Elia for procedural widget generation nodes.

> Adriano D'Elia [Link](https://linktr.ee/adrianodelia)

#### Authored and maintained by Gianluca Giampuzzo

